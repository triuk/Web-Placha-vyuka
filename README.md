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
- `Placha_versions_verified.csv` – strukturovaná tabulka 106 doložených verzí včetně role `PLA88`

## Přehled variant předmětů

Web zobrazuje primárně jeden řádek na kód předmětu. Jednotlivé Edison verze jsou dostupné po rozbalení.

Dvě verze se automaticky spojí do jedné generace pouze tehdy, pokud mají shodný rok zavedení a zrušení, počet kreditů a kompletní sadu forem studia (forma, způsob zakončení a rozsah) a současně tvoří jednoznačný pár čeština + angličtina. Dvě české nebo dvě anglické verze se automaticky neslučují. Různé kódy předmětů se neslučují ani při stejném názvu.

Úplná neseskupená tabulka všech 106 doložených verzí zůstává na webu jako technický/auditní detail.

## Změna proti prvnímu reportu

Při novém přímém stažení Edisonu byla navíc identifikována verze `9360-0125/02` (Systém managementu kvality v laboratořích), 2010/2011–2023/2024. `PLA88` je na stránce uvedena jako přednášející. Žádná z původně doložených 105 verzí nezmizela; aktuální součet je 106. Výřez 2025/2026 zůstává 28 verzí / 14 předmětů.

Audit změny: `archive/pla88-delta.txt`; kontrolní souhrn: `archive/report-build.txt`.

## Známý rozdíl mezi zdroji Edison

U předmětu `9360-0903` uvádí oficiální PDF/XLS export název **„Metody instrumentální analýzy II.“**, zatímco archivovaná hlavní stránka a stránky konkrétních verzí Edison uvádějí **„Metody instrumentální analýzy II“** bez koncové tečky. Datová vrstva používá název z raw Edison stránky; oficiální export zůstává beze změny. Rozdíl je evidován v `archive/source-discrepancies.md`.

## Zdrojové podklady

Ve `sources/` jsou uloženy:

- původní seznam 54 Edison URL `Vsechny-predmety.txt`,
- **čtyři byte-for-byte originální oficiální exporty Edison** v `sources/official-edison-exports/` (`subject_list_platne.pdf/.xls` a `subject_list_vsechny.pdf/.xls`),
- textový souhrn exportu „Platné a budoucí“ (14 předmětů),
- textový souhrn exportu „Všechny“ (54 předmětů),
- SHA-256 pěti původních vstupních souborů v `sources/source-files.sha256`.

Originální PDF/XLS byly převzaty z připojeného Google Drive přes autorizované API. Před uložením na GitHub byly ověřeny proti původním SHA-256; nejde o převod ani nově vygenerovaný export.

## Automatická kontrola konzistence

`scripts/audit_project.py` kontroluje celý projekt a workflow `.github/workflows/consistency.yml` jej spouští při každém pull requestu a změně `main`.

Audit ověřuje zejména:

- počty 54 + 122 raw HTML souborů a úplnost obou manifestů,
- velikost a SHA-256 všech 176 raw HTML souborů,
- shodu `data.js`, `Placha_versions_verified.csv`, manifestu a raw HTML,
- názvy, role `PLA88`, Edison URL a příznaky 2025/2026,
- přesné SHA-256 všech pěti původních zdrojových souborů,
- konzervativní seskupování CZ/EN variant a zachování více forem studia,
- syntaxi JavaScriptu, interní odkazy, úplnost indexu archivu a absenci závislosti na Drive URL.

## Interpretace

Report dokládá, že konkrétní archivovaná stránka verze obsahovala kód `PLA88`, a uvádí metadata `Rok zavedení` / `Rok zrušení`. Údaj `Rok zrušení 2025/2026` sám o sobě **není důkazem**, že se předmět v akademickém roce 2025/2026 skutečně realizoval se zapsanými studenty.

U každé verze web nabízí offline raw HTML uložené přímo v GitHubu, původní živý odkaz na Edison a SHA-256 archivované stránky. Web ani raw HTML archiv nejsou závislé na Google Drive.
