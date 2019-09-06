#TODO: 异常处理， 客户端或配置文件单独更新
$telegraf_root_path = "${Env:ProgramFiles}\telegraf"
$URL_root_path = "http://169.254.169.254:10051/"
$telegraf_service = Get-Service "telegraf" -ErrorAction 'SilentlyContinue'

if ($telegraf_service.Status -eq 'Running') {
    $telegraf_service.Stop()
    $telegraf_service.WaitForStatus('Stopped')
}

$client = new-object System.Net.WebClient
$url = "$URL_root_path/windows/telegraf.exe"
$output = "$telegraf_root_path\telegraf.exe"
Write-Host "Downloading telegraf.exe"
$client.DownloadFile($url, $output)

$telegraf_conf_path = "$telegraf_root_path\telegraf.conf"

$url = "$URL_root_path/windows/telegraf.conf"

Write-Host "Downloading telegraf.conf"
$client.DownloadFile($url, $telegraf_conf_path)

$telegraf_conf_path = "$telegraf_root_path\telegraf.conf"

if (-not (Test-Path -path "C:\zabbix_agent\conf\zabbix_agentd.win.conf")) {
    Write-Host "Zabbix conf does not exist, please update vm_uuid in $telegraf_conf_path manully"
    Exit
}

$zabbix_conf = "$(Get-Content C:\zabbix_agent\conf\zabbix_agentd.win.conf)"
$reg = "\b[0-9a-z]{8}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12}\b"
$h = $zabbix_conf -match $reg
$zabbix_uuid = $matches[0]

(Get-Content $telegraf_conf_path) -replace "xxx_uuid_to_replace_xxx". $zabbix_uuid | Set-Content $telegraf_conf_path

Set-Location -Path $telegraf_root_path


if ($telegraf_service) {
    Write-Host "Restart telegraf service"
    .\telegraf.exe --service start
} else {
    Write-Host "Install telegraf service & start"
    .\telegraf.exe --service install
    .\telegraf.exe --service start
}

$telegraf_service = Get-Service "telegraf" -ErrorAction 'SilentlyContinue'
if ($telegraf_service.Status -eq "Running") {
    Write-Host "Telegraf has already updated"
} else {
    Write-Host "Something is wrong, contact technique plz"
}
