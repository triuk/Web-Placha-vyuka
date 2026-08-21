# Web-Placha-vyuka

Samostatný GitHub archiv a webový report evidence předmětů VŠB/Edison spojených s osobním číslem `PLA88` (prof. Ing. Daniela Plachá, Ph.D.).

Web: **https://triuk.github.io/Web-Placha-vyuka/**

## Archiv

- 54 hlavních stránek předmětů v `archive/subjects/`
- 122 stránek konkrétních verzí v `archive/versions/`
- 106 verzí, jejichž raw HTML při stažení 21. 8. 2026 obsahovalo `PLA88`
- 28 verzí / 14 předmětů relevantních pro akademický rok 2025/2026 podle pravidla použitého v reportu
- `archive/index.html` – úplný index offline stránek s původními Edison odkazy a SHA-256
- `archive/manifest.csv` a `archive/manifest.json` – manifest všech 176 raw HTML souborů
- `Placha_versions_verified.csv` – strukturovaná tabulka 106 doložených verzí

## Změna proti prvnímu reportu

Při novém přímém stažení Edisonu byla navíc identifikována verze `9360-0125/02` (Systém managementu kvality v laboratořích), 2010/2011–2023/2024. `PLA88` je na stránce uvedena jako přednášející. Žádná z původně doložených 105 verzí nezmizela; aktuální součet je 106. Výřez 2025/2026 zůstává 28 verzí / 14 předmětů.

Audit: `archive/pla88-delta.txt`; kontrolní souhrn: `archive/report-build.txt`.

## Zdrojové podklady

Ve `sources/` jsou uloženy:

- původní seznam 54 Edison URL `Vsechny-predmety.txt`,
- textový souhrn exportu „Platné a budoucí“ (14 předmětů),
- textový souhrn exportu „Všechny“ (54 předmětů),
- SHA-256 pěti původních vstupních souborů.

Originální PDF/XLS exporty nebylo možné z Google Drive stáhnout přímo na GitHub runner bez autentizace; nejsou proto vydávány za archivované binární kopie. Jejich obsahově podstatný seznam a filtry jsou zachovány v textových souhrnech a jejich originální kontrolní součty v `sources/source-files.sha256`.

## Interpretace

Report dokládá, že konkrétní archivovaná stránka verze obsahovala kód `PLA88`, a uvádí metadata `Rok zavedení` / `Rok zrušení`. Údaj `Rok zrušení 2025/2026` sám o sobě **není důkazem**, že se předmět v akademickém roce 2025/2026 skutečně realizoval se zapsanými studenty.

U každé verze web nabízí offline raw HTML uložené přímo v GitHubu, původní živý odkaz na Edison a SHA-256 archivované stránky. Web ani raw HTML archiv nejsou závislé na Google Drive.
