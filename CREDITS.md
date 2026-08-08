# Credits

This project combines local build tooling with external Icelandic language resources.

## Data Sources

- Stofnun Árna Magnússonar í íslenskum fræðum
- CLARIN Iceland distribution channels and metadata records

Primary repository reference:
- https://repository.clarin.is/

### Optional Enrichment Data (Pronunciation & Hyphenation)

- Pronunciation Dictionary for Icelandic (Hjal-project), CC BY 3.0 —
  https://repository.clarin.is/repository/xmlui/handle/20.500.12537/198
- Icelandic Hyphenation Dictionary 2.0, CC BY 4.0 —
  https://repository.clarin.is/repository/xmlui/handle/20.500.12537/86
  (upstream source: https://github.com/krunars/hyphenation-is)

Both published by Stofnun Árna Magnússonar í íslenskum fræðum and, unlike
the INO data below, licensed CC BY — redistribution of derived output is
permitted with attribution.

### Optional Enrichment Data (Synonyms)

- IceWordNet (Icelandic Core WordNet), CC BY 3.0 —
  https://repository.clarin.is/repository/xmlui/handle/20.500.12537/207
  Icelandic translations and synonyms based on the Princeton Core WordNet
  list, compiled by Kristín M. Jóhannsdóttir with help from the Icelandic
  Thesaurus (Svavar Sigmundsson 1985) and snara.is.

Published by Stofnun Árna Magnússonar í íslenskum fræðum, licensed CC BY —
redistribution of derived output is permitted with attribution.

## Morphology and Lookup Runtime

Inflected-form lookup and paradigm tables are derived from BÍN
(Beygingarlýsing íslensks nútímamáls / Database of Icelandic Morphology),
https://bin.arnastofnun.is/. The copyright holder is Stofnun Árna
Magnússonar í íslenskum fræðum (The Árni Magnússon Institute for Icelandic
Studies), and the data are used under the terms of the
[CC BY-SA 4.0 license](https://creativecommons.org/licenses/by-sa/4.0/legalcode)
(terms: https://bin.arnastofnun.is/DMII/LTdata/conditions/).

In accordance with the BÍN license terms, credit is hereby given as follows.
**DO NOT EDIT, PARAPHRASE, TRANSLATE, ABBREVIATE, OR REFLOW the indented
line below** — BÍN's terms require this exact wording, and it is reproduced
verbatim from the citation form the copyright holder prescribes:

    Beygingarlýsing íslensks nútímamáls. Stofnun Árna Magnússonar í íslenskum fræðum.
    Höfundur og ritstjóri Kristín Bjarnadóttir.

BÍN is accessed through the `islenska` (BinPackage) Python package,
Copyright © Miðeind ehf., original author Vilhjálmur Þorsteinsson. Neither
Miðeind ehf. nor this project claims any endorsement, sponsorship, or
official status granted by the BÍN copyright holder.

## Tooling and Packaging

- Dictionary conversion/build scripts and packaging in this repository:
  Jónatan Sólon and contributors

## License Reminder

Source lexical datasets may be distributed under CC BY-NC-ND 4.0 terms.
Do not redistribute compiled dictionary bundles or modified source data unless upstream licensing explicitly permits it.
