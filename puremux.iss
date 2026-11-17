[Setup]
AppName=PureMUX
AppVersion=1.7
AppPublisher=Aahil Admani
DefaultDirName={autopf}\PureMUX
DefaultGroupName=PureMUX
DisableProgramGroupPage=yes
OutputBaseFilename=PureMUX_Setup_v1.7
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; This grabs everything inside your dist\PureMUX folder and bundles it into the installer
Source: "C:\Users\Aahil Admani\Desktop\NovaFetch\dist\PureMUX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Creates a desktop shortcut
Name: "{autodesktop}\PureMUX"; Filename: "{app}\PureMUX.exe"; IconFilename: "{app}\icon.ico"
; Creates a Start Menu shortcut
Name: "{autoprograms}\PureMUX\PureMUX"; Filename: "{app}\PureMUX.exe"; IconFilename: "{app}\icon.ico"

[Run]
; Option to launch the app immediately after installation finishes
Filename: "{app}\PureMUX.exe"; Description: "Launch PureMUX v1.7"; Flags: nowait postinstall skipifsilent