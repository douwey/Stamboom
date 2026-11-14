# Stamboom Genesis

Maakt van een csv met personen een stamboom als één HTML-pagina. Generaties staan op gelijke hoogte,
partners naast elkaar en kinderen eronder. Takken zijn in- en uitklapbaar, en je kunt zoeken op naam.

## Gebruik

```
python3 build.py genesis.csv stamboom.html
```

Open daarna `stamboom.html` in een browser. Je hebt alleen Python 3 nodig, geen extra pakketten.

## Kolommen in de csv

`id, vader id, moeder id, partner id, naam, mv, geboren, overleden, leeftijd, vader, partner, moeder, comment`

Alleen `id`, `vader id`, `moeder id`, `partner id`, `naam` en `mv` worden gebruikt voor de indeling.
Bij meerdere partners staan de ids gescheiden door een komma, bijvoorbeeld `"13,14"`.

## Uitgangspunten

- De csv klopt. Wie samen kinderen kreeg, vormt een gezin en staat naast elkaar met een huwelijkslijn.
- Een partner zonder kinderen staat naast zijn partner. Zou dat een kind in het gezin van zijn eigen ouders zetten,
  dan krijgt het paar een gestippelde lijn.
- Het geslacht volgt de rol: wie `moeder id` van iemand is, wordt als vrouw getoond, wie `vader id` is als man.
- Een stamboom die alleen via een aangetrouwde partner aan de hoofdboom hangt, wordt gekoppeld en opent met het
  knopje "afkomst". Stambomen zonder koppeling staan los rechts naast de hoofdboom.
- Opmerkingen over de gegevens (aangepast geslacht, gestippelde lijnen, gekoppelde takken) staan in de pagina onder "Notities".

## Opbouw

- `build.py` leest de csv, bepaalt gezinnen, generaties en gekoppelde takken en schrijft die als gegevens in de pagina.
- `template.html` bevat de pagina met de indeling (rijen en kolommen), het in- en uitklappen en het zoeken.
  De pagina rekent de indeling in de browser uit.
