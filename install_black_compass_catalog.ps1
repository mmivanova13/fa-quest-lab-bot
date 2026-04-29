# Run this script from the root folder of your Telegram bot project.
# It adds or updates COMPASS2026 in quest_catalog.json without deleting other quests.

$CatalogPath = "quest_catalog.json"

if (!(Test-Path $CatalogPath)) {
    Write-Error "quest_catalog.json not found. Run this script from the bot project root folder."
    exit 1
}

$catalog = Get-Content $CatalogPath -Raw | ConvertFrom-Json

$entry = [PSCustomObject]@{
    title = "The Black Compass Route"
    file = "quests/black_compass_route.json"
    active = $true
    description = "Trace the cargo before the river swallows the route."
    cover_image = "assets/black_compass_route_cover.png"
    cover_caption = "THE BLACK COMPASS ROUTE`n`nTrace the cargo before the river swallows the route.`n`nA pirate adventure in supply chains and trade"
}

# Add or replace property COMPASS2026.
$catalog | Add-Member -NotePropertyName "COMPASS2026" -NotePropertyValue $entry -Force

$catalog | ConvertTo-Json -Depth 50 | Set-Content -Path $CatalogPath -Encoding UTF8

Write-Host "Added/updated COMPASS2026 in quest_catalog.json"
Write-Host "Now run: git add . ; git commit -m 'Add The Black Compass Route quest' ; git push"
