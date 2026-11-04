#define AppName "Paint Overlay"
#define AppVersion "2.1.1"
[Setup]
AppId={{7D336D42-658B-4967-B2A9-797102AFF3DC}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Paint Overlay
DefaultDirName={localappdata}\Programs\Paint Overlay
DefaultGroupName=Paint Overlay
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DisableDirPage=no
WizardStyle=modern
WizardSizePercent=110
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\Paint Overlay.exe
OutputDir=..\dist
OutputBaseFilename=Paint Overlay Setup
Compression=lzma2
SolidCompression=yes
MinVersion=10.0
CloseApplications=yes
RestartApplications=no
AppMutex=Local\PaintOverlay.App,Local\JustPointer.App
VersionInfoVersion=2.1.1.0
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"
Name: "autostart"; Description: "Запускать Paint Overlay при входе в Windows"; GroupDescription: "Автозапуск:"
[Files]
Source: "..\dist\Paint Overlay.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
[InstallDelete]
Type: files; Name: "{app}\Just Pointer.exe"
Type: files; Name: "{autodesktop}\Just Pointer.lnk"
Type: files; Name: "{userprograms}\Just Pointer\Just Pointer.lnk"
Type: files; Name: "{userprograms}\Just Pointer\Удалить Just Pointer.lnk"
Type: files; Name: "{userstartup}\Just Pointer.lnk"
Type: files; Name: "{app}\Uninstall.cmd"
[Icons]
Name: "{group}\Paint Overlay"; Filename: "{app}\Paint Overlay.exe"
Name: "{group}\Удалить Paint Overlay"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Paint Overlay"; Filename: "{app}\Paint Overlay.exe"; Tasks: desktopicon
Name: "{userstartup}\Paint Overlay"; Filename: "{app}\Paint Overlay.exe"; Tasks: autostart
[Run]
Filename: "{app}\Paint Overlay.exe"; Description: "Запустить Paint Overlay"; Flags: nowait postinstall skipifsilent
