[Setup]
AppName=IPLapse
AppVersion=1.0.0
AppPublisher=IPLapse
DefaultDirName={autopf}\IPLapse
DefaultGroupName=IPLapse
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=IPLapse-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\IPWebcamTimelapse.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\IPLapse"; Filename: "{app}\IPWebcamTimelapse.exe"
Name: "{autodesktop}\IPLapse"; Filename: "{app}\IPWebcamTimelapse.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\IPWebcamTimelapse.exe"; Description: "Launch IPLapse now"; Flags: nowait postinstall skipifsilent