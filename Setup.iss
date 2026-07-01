; Word Chain Game - Multiplayer Installer
; Created with Inno Setup

#define MyAppName "Word Chain Game - Multiplayer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Vasudev"

[Setup]
AppId={{F240A53C-FBE1-4B21-A3CD-7B7519F4BDCE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; Install into the current user's Local AppData
DefaultDirName={localappdata}\Word Chain Game

DefaultGroupName={#MyAppName}

; Current-user install (no admin required)
PrivilegesRequired=lowest

OutputDir=Output
OutputBaseFilename=WordChainGameSetup

SetupIconFile=icon.ico

Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; Only include the launcher exe and the installer icon
Source: "Launcher\WordChainGameLauncher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Word Chain Game - Multiplayer"; \
    Filename: "{app}\WordChainGameLauncher.exe"; \
    WorkingDir: "{app}"; \
    IconFilename: "{app}\icon.ico"

Name: "{autodesktop}\Word Chain Game - Multiplayer"; \
    Filename: "{app}\WordChainGameLauncher.exe"; \
    WorkingDir: "{app}"; \
    IconFilename: "{app}\icon.ico"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\WordChainGameLauncher.exe"; \
    WorkingDir: "{app}"; \
    Description: "Launch Word Chain Game - Multiplayer"; \
    Flags: postinstall nowait skipifsilent