param([string]$InnoCompiler)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (!(Test-Path '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create venv' }
}
$pythonExe = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
& $pythonExe -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $pythonExe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $pythonExe -m PyInstaller --noconfirm --clean --onefile --windowed --name 'Paint Overlay' --icon assets/app.ico --add-data 'assets;assets' --distpath dist --workpath build --specpath . src/paint_overlay.py
if ($LASTEXITCODE -ne 0) { throw 'Executable build failed' }
if (!$InnoCompiler) {
    $compilerCmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($compilerCmd) { $InnoCompiler = $compilerCmd.Source }
    else {
        foreach ($candidate in @('${env:ProgramFiles(x86)}/Inno Setup 6/ISCC.exe', '$env:LOCALAPPDATA/Programs/Inno Setup 6/ISCC.exe')) {
            $expanded = $ExecutionContext.InvokeCommand.ExpandString($candidate)
            if (Test-Path $expanded) { $InnoCompiler = $expanded; break }
        }
    }
}
if (!$InnoCompiler) { throw 'Inno Setup 6 not found. Pass -InnoCompiler.' }
& $InnoCompiler packaging/setup.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
