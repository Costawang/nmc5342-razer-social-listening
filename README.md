# NMC5342 — Razer Social Listening and NLP Data Preprocessing

*Data Cleaning and Corpus Construction for Social Media Discourse Analysis*

## Project overview

This academic research project is associated with **NUS NMC5342 — Social Media Analytics**. It investigates social media discourse surrounding Razer, including brand perception, product-related feedback, gaming culture, and negative audience sentiment.

This repository documents a Brand24 data export and the existing preprocessing pipeline used to construct a corpus for subsequent analysis. Topic modeling and sentiment validation are planned work; this repository does not present completed models or research findings.

## Research objectives

- Examine how discourse about Razer relates to product marketing, esports fandom, and gaming culture.
- Investigate negative audience discourse and identify potentially actionable product or brand concerns.
- Construct a relevant, traceable research corpus for subsequent natural language processing (NLP).

The Brand24 dataset primarily supports the social-listening component of the broader project. Inclusion in the final corpus is based on the implemented screening rules, not on negative sentiment alone.

## Data source

The source is a **Brand24 mentions export supplied for the course project**: `razer_report_2026-09-24_04.52 (1).xlsx`. This description does not attribute direct data collection to the research team.

The original `Mentions` worksheet contains **17,544 records**, with recorded dates from **2026-08-23 through 2026-09-24**, inclusive. Its first row is blank and its second row contains the column headers. The filename encodes `2026-09-24_04.52`; the export timezone is not established here. The workbook also contains `Sentiment`, `Categories`, `Numerical data`, and `Analytics data` worksheets, all preserved unchanged.

Available mention metadata comprises `ID`, `Date`, `Hrs`, `Title`, `Content`, `Source`, `Domain`, `Category`, `Sentiment`, and `Tags`. The worksheet also has an unlabeled leading column, read into the first two CSV stages as `Unnamed: 0`. The existing final-stage script removes that column. `Source` contains source URLs. Titles and text may identify accounts or individuals; some earlier-stage text also contains email-like strings.

The export includes news, other social platforms, TikTok, videos, blogs, web pages, and podcasts. It is not a representative sample of all Razer customers or all online discussion. Search configuration, platform coverage, and complete source text cannot be reconstructed from this export alone. The supplied `Sentiment` field is retained as source metadata and is not presented as independently validated sentiment.

## Data processing pipeline

The three scripts are preserved byte for byte. Each stage retains identifiers and available metadata for provenance.

### Stage 1 — Non-empty Content filtering

`script/clean_razer.py` searches the configured dataset directory for exactly one `razer_report*.xlsx` file, ignoring Excel lock files beginning with `~$`. It reads `Mentions` with `header=1` and preserves `ID` as a string. Records with missing or whitespace-only `Content` are removed, and retained rows are exported as UTF-8 with a byte-order mark (BOM). All available columns are retained.

### Stage 2 — Rule-based screening

`script/clean_razer_stage2.py` preserves original `Content` and creates `Content_clean` by decoding HTML entities, removing URLs and `[...]` markers, and collapsing whitespace. It adds:

- `Truncated_hint`: original content length of at least 249 characters, a diagnostic heuristic rather than proof of truncation.
- `Duplicate_text_hint`: repeated combinations of `Domain`, `Title`, and `Content`; this stage flags duplicates without removing them.
- `decision` and `reason`: rule-based screening outcomes and the first applicable screening reason.

Rows start as `KEEP`. Rules only update rows still labeled `KEEP`, so their order determines precedence. The rules screen Twitch stream metadata, Telegram gift-card advertising, merchant pages, and recruitment listings; separate news/web/blog/podcast sources, YouTube descriptions, and specified official TikTok accounts as context; and flag uncertain promotional, resale, news-repost, Telegram, short, or visibly unbranded content for review. Razer Insider is an exception to the general contextual-source rule.

| Decision | Records | Interpretation |
| --- | ---: | --- |
| KEEP | 3,943 | Candidate discourse retained by the screening rules |
| REVIEW | 540 | Uncertain content flagged by rules |
| CONTEXT | 3,355 | Contextual/editorial or specified brand material |
| EXCLUDE | 1,646 | Material excluded by the implemented rules |

The script writes the full labeled CSV and four decision-specific CSVs. Only the full labeled CSV is included in this repository; the four intermediate subsets are deliberately excluded.

### Stage Final — Topic-modeling corpus construction

`script/build_razer_stage_final.py` initially selects Stage 2 `KEEP` records and qualifying `REVIEW` records. Recovery uses the combined title and cleaned content:

1. A `possible_news_repost` record must contain a first-person expression and a Razer mention, without matching the promotional pattern.
2. A `no_razer_in_visible_title_or_text` record must contain a configured product/ecosystem term and a first-person expression.

The script then filters configured off-topic meanings of Razer, promotional patterns on Bluesky/TikTok, Reddit resale listings, Reddit deal announcements, and texts shorter than 15 characters. It builds `topic_text` from `Content_clean`, decodes HTML entities, removes a specific Reddit interface-residue pattern, and normalizes whitespace.

Exact duplicate `topic_text` values are removed **globally after case folding**, retaining the first occurrence. This is not semantic or near-duplicate detection. The original Stage 2 labels become `stage2_decision` and `stage2_reason`, and every final row receives `final_decision=KEEP`. The script removes `Unnamed: 0` and `Duplicate_text_hint` while retaining other provenance fields.

The saved final corpus contains **3,424 documents**: **3,416** originally labeled `KEEP` and **8** originally labeled `REVIEW` (7 possible news reposts and 1 product-context recovery). These are the surviving counts after filtering and deduplication, not counts of all initially recoverable records. REVIEW recovery is automated; the labels do not demonstrate completed human review.

## Dataset summary

Counts below were calculated directly from the checked-in source files. CSV counts exclude headers and use a CSV parser, so quoted multiline text does not inflate record counts. The Excel count uses mention records, excluding its blank first row and header row.

| Dataset stage | File | Records | Purpose |
| --- | --- | ---: | --- |
| Original export | `dataset/razer_report_2026-09-24_04.52 (1).xlsx` | 17,544 | Original Brand24 export and summary worksheets |
| Stage 1 | `dataset/razer_mentions_content_nonempty.csv` | 9,484 | Mentions with non-empty Content |
| Stage 2 | `dataset/stage2/razer_stage2_all_with_labels.csv` | 9,484 | All Stage 1 records with screening labels and reasons |
| Stage Final | `dataset/stage_final/razer_stage_final.csv` | 3,424 | Selected, filtered, deduplicated modeling documents |

The final corpus covers recorded dates **2026-08-23 through 2026-09-23**. Deduplicated modeling documents are not equivalent to the original number of Brand24 mentions. The final rows should not automatically be interpreted as unique consumers or independently verified consumer opinions.

## Reproducibility

### Environment and dependencies

The inspected local environment is Windows with **Python 3.14.8**, **pandas 3.1.0**, **openpyxl 3.1.5**, and **NumPy 2.5.4**. Use Python 3.14 to match that environment; other Python versions have not been validated for this repository. `requirements.txt` pins the two direct third-party dependencies: pandas and openpyxl. NumPy is a transitive pandas dependency; this minimal requirements file is not a complete environment lock.

The other imports (`pathlib`, `re`, and `html`) belong to the Python standard library. No LDA, BERTopic, or sentiment-model packages are needed to run these preprocessing scripts.

### Directory layout

```text
nmc5342-razer-social-listening/
├── dataset/
│   ├── razer_report_2026-09-24_04.52 (1).xlsx
│   ├── razer_mentions_content_nonempty.csv
│   ├── stage2/
│   │   └── razer_stage2_all_with_labels.csv
│   └── stage_final/
│       └── razer_stage_final.csv
├── script/
│   ├── clean_razer.py
│   ├── clean_razer_stage2.py
│   └── build_razer_stage_final.py
├── README.md
├── requirements.txt
└── .gitignore
```

### Paths, setup, and execution order

**The preserved scripts use the absolute Windows path `F:\NMC5342`.** Changing the shell's working directory does not redirect their data access. For reproduction, use a separate working copy placed at that path on an appropriate machine. If using a different location, change only the `folder` assignment in Stage 1 and the `ROOT` assignment in Stages 2 and Final in your own local script copies. The repository retains the original source files unchanged.

**Running the scripts overwrites the corresponding generated CSVs**, including the four Stage 2 subset files. Preserve any existing research outputs before rerunning. The publication audit did not execute the cleaning scripts against the original data directory.

For a working copy at `F:\NMC5342`, run in PowerShell:

```powershell
Set-Location 'F:\NMC5342'
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe .\script\clean_razer.py
.\.venv\Scripts\python.exe .\script\clean_razer_stage2.py
.\.venv\Scripts\python.exe .\script\build_razer_stage_final.py
```

| Script | Input | Output |
| --- | --- | --- |
| `clean_razer.py` | One `dataset/razer_report*.xlsx`, worksheet `Mentions` | `dataset/razer_mentions_content_nonempty.csv` |
| `clean_razer_stage2.py` | Stage 1 CSV | `dataset/stage2/razer_stage2_all_with_labels.csv` and four ignored decision subsets |
| `build_razer_stage_final.py` | Full Stage 2 labeled CSV | `dataset/stage_final/razer_stage_final.csv` |

Publication checks cover file integrity, CSV readability, row counts, syntax, ID linkage, preservation of Stage 1 Content in Stage 2, and non-empty, case-fold-unique final `topic_text`. They do not establish a fresh end-to-end pipeline rerun.

## Methodological limitations

- **Coverage and source bias:** Brand24 coverage, export selection, and source mix limit representativeness. News articles, video descriptions, brand posts, and user discourse are different units of analysis.
- **Excerpt truncation:** Visible `[...]` markers occur in the export. The length-based `Truncated_hint` is only a heuristic, and removing the marker does not recover omitted text. The final file retains 1,604 truncation hints and 1,188 records with `[...]` in original Content.
- **Rule-based errors:** Domain/category rules, English-language patterns, product terms, rule precedence, and text thresholds may produce false inclusions or exclusions. First-person language is not proof of genuine consumer authorship.
- **Review status:** Automated KEEP labels and recovered REVIEW records are not equivalent to fully human-validated annotations.
- **Deduplication:** Keeping one case-folded text occurrence removes repeated-text frequency and may collapse distinct mentions with identical excerpts. Use earlier-stage records for frequency questions with an appropriate definition of a mention.
- **Sentiment and inference:** The retained source sentiment labels require validation. Mention counts and the resulting corpus do not directly measure customer prevalence, causal effects, or population-level brand attitudes.

## Research team / Contributors

All three people are research co-authors:

| Name | GitHub |
| --- | --- |
| Wang Xinyang | [Costawang](https://github.com/Costawang) |
| Li Yunrui | [Michelle0622-li](https://github.com/Michelle0622-li) |
| Wu Xia | [hlengiwewu-star](https://github.com/hlengiwewu-star) |

## Next research steps

These are planned analyses, not completed findings:

1. Descriptive exploratory analysis of corpus composition and source distributions.
2. Sentiment validation against a human-reviewed sample.
3. Topic modeling using LDA and/or BERTopic.
4. Human-in-the-loop theme interpretation.
5. Identification of actionable brand concerns.
6. Integration into the NMC5342 final report.

## Data use and acknowledgement

We acknowledge **Brand24** as the source of the export used for this academic course project. Third-party social media and web content remains subject to applicable rights and conditions.

This repository is intended for **private research access**. Repository access and downstream distribution must respect applicable platform terms, copyright, privacy considerations, and course data-sharing conditions. No license is granted here for third-party content, and private repository access does not establish permission for public redistribution. The applicable reuse permissions have not been independently established by this publication audit.

## File integrity

The four datasets and three scripts are preserved byte for byte from the inspected local project. The table below allows independent checks without running the cleaning pipeline.

<details>
<summary>Source file sizes and SHA-256 checksums</summary>

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `dataset/razer_report_2026-09-24_04.52 (1).xlsx` | 1,909,020 | `e06aa246b636400889b7522e130d90c6dd3d472ffc57b4c03b86e473b6ad780d` |
| `dataset/razer_mentions_content_nonempty.csv` | 3,633,440 | `450c39d6cc16686357e91c70e3868116434129d07ba78a248976877cbd61266b` |
| `dataset/stage2/razer_stage2_all_with_labels.csv` | 5,832,145 | `a6d1e830ef828b976da5edb3c47e836baecbd0dcab02d7c030c3556f47bdd23b` |
| `dataset/stage_final/razer_stage_final.csv` | 2,681,028 | `24c715aff903c2e2d3272c9f47fcabb574c321aaba6d0956bdc6d93497341089` |
| `script/clean_razer.py` | 1,227 | `9e93855d5c8707ff75295fff001494f0514f965deb999fbb6d375c5d46ab1149` |
| `script/clean_razer_stage2.py` | 6,314 | `efe3392d9f93e6e22b10eb432539080c8cd3233b20ab9c42ac23c1f18f4a7e78` |
| `script/build_razer_stage_final.py` | 6,926 | `8e993d0ed629d3e52edb521d33a088a0f489ee19d4e344b1266b80215260f2fa` |

</details>
