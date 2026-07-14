# Ejecutar como Administrador: clic derecho -> Ejecutar con PowerShell (como admin)
$ruleName = "Valorant Stat Phone API"
$existing = netsh advfirewall firewall show rule name="$ruleName" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Regla ya existe: $ruleName"
} else {
    netsh advfirewall firewall add rule name="$ruleName" dir=in action=allow protocol=TCP localport=8080
    Write-Host "Puerto 8080 abierto para la ESP32."
}
Write-Host "Listo. Pulsa RESET en la ESP32."
