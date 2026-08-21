# Známé rozdíly mezi zdroji Edison

Tento soubor eviduje rozdíly, které nejsou způsobeny zpracováním archivu, ale jsou přítomné už v samotných zdrojích systému Edison.

## 9360-0903

- Oficiální export `subject_list_platne.pdf/.xls` a odvozený textový souhrn uvádějí název **„Metody instrumentální analýzy II.“** (s tečkou na konci).
- Archivovaná hlavní stránka Edison `archive/subjects/subject_9360-0903.html` uvádí **„Metody instrumentální analýzy II“** (bez tečky).
- Archivované stránky konkrétních verzí `9360-0903/01` až `/04` rovněž uvádějí název bez tečky.

Datová vrstva reportu (`data.js`, `Placha_versions_verified.csv`) používá název z raw stránky Edison, tedy bez koncové tečky. Oficiální export je zachován byte-for-byte a jeho textový souhrn se kvůli tomuto rozdílu neupravuje.

Jde pouze o interpunkční rozdíl v názvu; kód předmětu `9360-0903` je ve všech zdrojích shodný.
