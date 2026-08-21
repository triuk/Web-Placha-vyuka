# Web-Placha-vyuka

Samostatný archiv a webový report evidence předmětů VŠB/Edison spojených s osobním číslem `PLA88` (prof. Ing. Daniela Plachá, Ph.D.).

Web: **https://triuk.github.io/Web-Placha-vyuka/**

## Obsah archivu

- 54 hlavních stránek předmětů v `archive/subjects/`
- 122 stránek konkrétních verzí v `archive/versions/`
- 106 verzí, jejichž raw HTML při stažení 21. 8. 2026 obsahovalo `PLA88`
- 28 verzí / 14 předmětů vyhodnocených jako relevantní pro akademický rok 2025/2026 podle metadat reportu
- `archive/index.html` – úplný index offline stránek s původními odkazy na Edison a SHA-256
- `archive/manifest.csv` a `archive/manifest.json` – manifest všech 176 raw HTML souborů
- `Placha_versions_verified.csv` – strukturovaná tabulka 106 doložených verzí s PLA88
- `sources/` – původní vstupní seznam a exporty Edisonu

## Změna proti prvnímu reportu

Při novém přímém stažení Edisonu byla navíc identifikována verze `9360-0125/02` (Systém managementu kvality v laboratořích), 2010/2011–2023/2024. Na stránce je `PLA88` uvedena jako přednášející. Žádná z původně doložených 105 verzí nezmizela, takže aktuální součet je 106.

Tato změna neovlivňuje výřez 2025/2026: zůstává 28 verzí / 14 předmětů.

Audit rozdílu je uložen v `archive/pla88-delta.txt` a kontrolní souhrn v `archive/report-build.txt`.

## Interpretace dat

Report dokládá, že konkrétní archivovaná stránka verze obsahovala kód `PLA88`, a uvádí metadata `Rok zavedení` a `Rok zrušení`. Údaj `Rok zrušení 2025/2026` sám o sobě **není důkazem**, že se předmět v akademickém roce 2025/2026 skutečně realizoval se zapsanými studenty.

U každé verze web nabízí:

1. offline raw HTML uložené v tomto repozitáři,
2. původní živý odkaz na Edison,
3. SHA-256 archivované stránky.

## Integrita

Aktuální archiv byl stažen přímo z `edison.sso.vsb.cz` pomocí GitHub Actions dne 21. 8. 2026. Downloader objevil přesně 122 konkrétních verzí pro 54 zadaných kódů. Úplný seznam URL, velikostí a SHA-256 je v `archive/manifest.*`.

Zdrojové exporty mají vlastní kontrolní součty v `sources/source-files.sha256`.

## Nezávislost na Google Drive

Web, report ani offline HTML archiv nemají být závislé na Google Drive. Všechny odkazy používané webem směřují buď na soubory v tomto GitHub repozitáři/GitHub Pages, nebo na původní veřejné stránky VŠB/Edison.
