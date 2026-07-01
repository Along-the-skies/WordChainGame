using System;
using System.Drawing;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.IO.Compression;
using System.Diagnostics;

namespace WordChainGameLauncher
{
    public partial class Form1 : Form
    {
        private Button buttonInstall;
        private Button buttonUpdate;
        private Button buttonPlay;
        private ProgressBar progressBar;
        private Label labelStatus;

        private string repoZipUrl = "https://github.com/Along-The-skies/WordChainGame/archive/refs/heads/main.zip";
        private string versionUrl = "https://raw.githubusercontent.com/Along-The-skies/WordChainGame/refs/heads/main/version.txt";
        private string extractPath = Path.Combine(Environment.CurrentDirectory, "WordChainGame");

        public Form1()
        {
            InitializeComponent();
            SetupUI();
        }

        private void SetupUI()
        {
            this.Text = "Word Chain Game - Multiplayer";
            this.Size = new Size(560, 500);
            this.StartPosition = FormStartPosition.CenterScreen;

            // Clickable repo link
            LinkLabel linkRepo = new LinkLabel();
            linkRepo.Text = "Repo: https://github.com/Along-The-skies/WordChainGame";
            linkRepo.Location = new Point(20, 20);
            linkRepo.AutoSize = true;
            linkRepo.LinkClicked += (s, e) =>
            {
                try
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = "https://github.com/Along-The-skies/WordChainGame",
                        UseShellExecute = true
                    });
                }
                catch (Exception ex)
                {
                    MessageBox.Show("Error opening link: " + ex.Message);
                }
            };
            Controls.Add(linkRepo);

            Label labelVersion = new Label();
            labelVersion.Text = "[ Version: Local Unknown ]";
            labelVersion.Location = new Point(20, 50);
            labelVersion.AutoSize = true;
            Controls.Add(labelVersion);

            buttonInstall = new Button();
            buttonInstall.Text = "INSTALL";
            buttonInstall.Size = new Size(120, 40);
            buttonInstall.Location = new Point(20, 100);
            buttonInstall.Click += async (s, e) => await InstallGame();
            Controls.Add(buttonInstall);

            buttonUpdate = new Button();
            buttonUpdate.Text = "UPDATE";
            buttonUpdate.Size = new Size(120, 40);
            buttonUpdate.Location = new Point(160, 100);
            buttonUpdate.Click += async (s, e) => await UpdateGame();
            Controls.Add(buttonUpdate);

            buttonPlay = new Button();
            buttonPlay.Text = "PLAY GAME";
            buttonPlay.Size = new Size(120, 40);
            buttonPlay.Location = new Point(300, 100);
            buttonPlay.Enabled = false;
            buttonPlay.Click += PlayGame;
            Controls.Add(buttonPlay);

            progressBar = new ProgressBar();
            progressBar.Location = new Point(20, 160);
            progressBar.Size = new Size(500, 25);
            Controls.Add(progressBar);

            labelStatus = new Label();
            labelStatus.Text = "Status: Waiting...";
            labelStatus.Location = new Point(20, 200);
            labelStatus.AutoSize = true;
            Controls.Add(labelStatus);
        }

        private async Task InstallGame()
        {
            string zipPath = Path.Combine(Path.GetTempPath(), "game.zip");

            try
            {
                using (var client = new HttpClient())
                {
                    labelStatus.Text = "Downloading game files...";
                    progressBar.Value = 20;

                    var data = await client.GetByteArrayAsync(repoZipUrl);
                    File.WriteAllBytes(zipPath, data);

                    progressBar.Value = 50;
                    labelStatus.Text = "Extracting files...";

                    if (Directory.Exists(extractPath))
                        Directory.Delete(extractPath, true);

                    ZipFile.ExtractToDirectory(zipPath, extractPath);

                    progressBar.Value = 100;
                    labelStatus.Text = "Install complete!";
                    buttonPlay.Enabled = true;

                    await InstallDependencies();
                }
            }
            catch (Exception ex)
            {
                labelStatus.Text = "Error: " + ex.Message;
            }
        }

        private async Task UpdateGame()
        {
            try
            {
                using (var client = new HttpClient())
                {
                    labelStatus.Text = "Checking for updates...";
                    var remoteVersion = await client.GetStringAsync(versionUrl);
                    string localVersion = "";

                    string localVersionFile = Path.Combine(extractPath, "version.txt");
                    if (File.Exists(localVersionFile))
                        localVersion = File.ReadAllText(localVersionFile).Trim();

                    if (remoteVersion.Trim() == localVersion)
                    {
                        labelStatus.Text = "Game is up to date.";
                        return;
                    }

                    labelStatus.Text = $"Updating to version {remoteVersion.Trim()}...";
                    await InstallGame();

                    File.WriteAllText(localVersionFile, remoteVersion.Trim());
                    labelStatus.Text = "Update complete!";
                }
            }
            catch (Exception ex)
            {
                labelStatus.Text = "Error updating: " + ex.Message;
            }
        }

        private async Task InstallDependencies()
        {
            try
            {
                string reqFile = Path.Combine(extractPath, "requirements.txt");
                if (File.Exists(reqFile))
                {
                    labelStatus.Text = "Installing dependencies...";
                    ProcessStartInfo psi = new ProcessStartInfo
                    {
                        FileName = "python",
                        Arguments = $"-m pip install -r \"{reqFile}\"",
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true
                    };
                    var proc = Process.Start(psi);
                    await proc.WaitForExitAsync();
                    labelStatus.Text = "Dependencies installed.";
                }
            }
            catch (Exception ex)
            {
                labelStatus.Text = "Error installing dependencies: " + ex.Message;
            }
        }

        private void PlayGame(object sender, EventArgs e)
        {
            try
            {
                string gameScript = Path.Combine(extractPath, "game.py");

                if (File.Exists(gameScript))
                {
                    ProcessStartInfo psi = new ProcessStartInfo
                    {
                        FileName = "python",
                        Arguments = $"\"{gameScript}\"",
                        WorkingDirectory = extractPath,
                        UseShellExecute = false
                    };
                    Process.Start(psi);
                    labelStatus.Text = "Game launched!";
                }
                else
                {
                    labelStatus.Text = "Error: game.py not found.";
                }
            }
            catch (Exception ex)
            {
                labelStatus.Text = "Error launching game: " + ex.Message;
            }
        }
    }
}
