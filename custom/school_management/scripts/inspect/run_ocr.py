import subprocess

images = [
    r'C:\Users\Rith2\AppData\Local\Temp\ai-chat-custom-attachment-temp-file-baa6a8f3-ed60-40ed-ae3a-2b9892a4df94-9866633899368056196.png'
]

ps_base = r'''
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }

function Await($winRtTask, $resultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($resultType)
    $netTask = $asTask.Invoke($null, @($winRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.FileAccessMode, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

$path = 'TARGET_IMAGE_PATH'

$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new("en-US"))
}

$ocrResult = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

foreach ($line in $ocrResult.Lines) {
    $b = $line.Words[0].BoundingRect
    Write-Output ("Y={0:D4} X={1:D4} : {2}" -f [int]$b.Y, [int]$b.X, $line.Text)
}
'''

for i, img in enumerate(images):
    print(f"\n=================== IMAGE {i+1} ===================")
    code = ps_base.replace('TARGET_IMAGE_PATH', img)
    with open(r'C:\Users\Rith2\AppData\Local\Temp\run_ocr_target.ps1', 'w', encoding='utf-8') as f:
        f.write(code)
    res = subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-File', r'C:\Users\Rith2\AppData\Local\Temp\run_ocr_target.ps1'], capture_output=True, text=True)
    lines = res.stdout.strip().splitlines()
    print('\n'.join(lines))
