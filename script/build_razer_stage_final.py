
import re
import html
import pandas as pd
from pathlib import Path

# =====================================
# 1. File paths
# =====================================

ROOT = Path(r"F:\NMC5342")
INPUT = ROOT / "dataset" / "stage2" / "razer_stage2_all_with_labels.csv"
OUTPUT_DIR = ROOT / "dataset" / "stage_final"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT = OUTPUT_DIR / "razer_stage_final.csv"

df = pd.read_csv(
    INPUT,
    encoding="utf-8-sig",
    dtype={"ID": "string"},
    low_memory=False
)

for col in ["Title", "Content", "Content_clean", "Domain", "decision", "reason"]:
    df[col] = df[col].fillna("").astype(str)

df["decision"] = df["decision"].str.strip().str.upper()
df["reason"] = df["reason"].str.strip()

full_text = df["Title"] + " " + df["Content_clean"]
domain = df["Domain"].str.strip().str.lower()

# =====================================
# 2. Select KEEP + recover valid REVIEW
# =====================================

# Known Razer product / ecosystem terminology
product_re = (
    r"\b(?:synapse|deathadder|blackshark|basilisk|"
    r"viper\s*v\d|huntsman|kraken(?:\s|$)|ornata|"
    r"wolverine(?:\s|$)|barracuda(?:\s|$)|kishi|"
    r"iskur|naga\s*v|blade\s*(?:\d|pro|stealth)|"
    r"chroma|razer\s*gold|seiren|axon|kiyo|nommo|"
    r"firefly|raiju|cobra\s*(?:pro|hyperspeed)|"
    r"book\s*\d?)\b"
)

# Detect personal expressions
first_person = full_text.str.contains(
    r"(?i)\b(?:i|i'm|i've|i'd|my|mine|me)\b",
    regex=True
)

brand_mention = full_text.str.contains(
    r"(?i)\brazer\b",
    regex=True
)

product_mention = full_text.str.contains(
    product_re,
    case=False,
    regex=True
)

# Common promotional content patterns
promo_re = (
    r"(?i)(?:#ad\b|#deals?\b|#tiktokshop\b|"
    r"#affiliate\b|\baffiliate\b|\bshop now\b|"
    r"\bbuy now\b|\blink in bio\b|"
    r"\bprice:\s*[$€£]|\breg\s*[$€£]|"
    r"\b\d+%\s*off\b|\bpromo\s*code\b|"
    r"\bdiscount\s*code\b|\blowest price\b)"
)

has_promo = full_text.str.contains(
    promo_re,
    regex=True
)

# Recover individual opinions mistakenly flagged
# as possible news reposts.
review_personal = (
    df["reason"].eq("possible_news_repost")
    & first_person
    & brand_mention
    & ~has_promo
)

# Recover relevant truncated product discussions
review_product = (
    df["reason"].eq("no_razer_in_visible_title_or_text")
    & product_mention
    & first_person
)

recover_review = (
    df["decision"].eq("REVIEW")
    & (review_personal | review_product)
)

selected = df[
    df["decision"].eq("KEEP") | recover_review
].copy()

initial_selected = len(selected)

# =====================================
# 3. Remove obvious irrelevant content
# =====================================

text = selected["Title"] + " " + selected["Content_clean"]
source = selected["Domain"].str.strip().str.lower()

# Unrelated meanings of "Razer"
offtopic_re = (
    r"(?i)(?:\bgreen lantern\b|\byoung justice\b|"
    r"\bred lantern razer\b|"
    r"\bmoto(?:rola)?\s+raz(?:e)?r\b|"
    r"\brazr\s*(?:20\d{2}|plus|ultra)\b|"
    r"\b(?:surron|sur-ron|talaria|can-?am|polaris)\b|"
    r"\bbarbershops?\b|\brazerburns?\b|"
    r"\bbikini\s*trimmer\b|\bbikinitrimmer\b|"
    r"\bfursona\b|"
    r"\brazer (?:the (?:sob|character)|is a man)\b)"
)

# Shaving/scraping contexts, not Razer hardware
blade_noise_re = (
    r"(?i)(?:\bshaving with (?:a )?razer blade\b|"
    r"\brazer blades?\b.{0,60}\b"
    r"(?:scrap(?:e|ing)|shav(?:e|ing))\b|"
    r"(?:scrap(?:e|ing)|shav(?:e|ing))\b"
    r".{0,60}\brazer blades?\b)"
)

offtopic = (
    text.str.contains(offtopic_re, regex=True)
    | text.str.contains(blade_noise_re, regex=True)
)

# Affiliate / promotional bot content
promotional = (
    source.isin(["bsky.app", "tiktok.com"])
    & text.str.contains(promo_re, regex=True)
)

# Marketplace resale posts on Reddit
resale_re = (
    r"(?i)(?:\b(?:selling|for sale|want to sell|"
    r"want to sale)\b|"
    r"^\s*\[(?:wts|wtb|sell)\]|^\s*wts\b)"
)

resale = (
    source.eq("reddit.com")
    & selected["Title"].str.contains(
        resale_re, regex=True
    )
)

# Automated Reddit discount announcements
reddit_deal_re = (
    r"(?i)(?:^\s*\[(?:amazon|ebay|deal)\]|"
    r"\bdeal alert\b|\b\d{1,3}%\s*off\b|"
    r"\bdiscount\s*code\b)"
)

reddit_deal = (
    source.eq("reddit.com")
    & selected["Title"].str.contains(
        reddit_deal_re, regex=True
    )
)

# =====================================
# 4. Prepare modeling text
# =====================================

def prepare_topic_text(value):
    value = html.unescape(value)

    # Remove common Reddit UI residue
    value = re.sub(
        r"(?i)\bUpvote\d*Downvote\d*"
        r"Go to commentsRepost\b",
        " ",
        value
    )

    value = re.sub(r"\s+", " ", value)
    return value.strip()


selected["topic_text"] = selected[
    "Content_clean"
].map(prepare_topic_text)

# Remove text with almost no usable information
too_short = selected["topic_text"].str.len().lt(15)

# Combined exclusion
remove_mask = (
    offtopic
    | promotional
    | resale
    | reddit_deal
    | too_short
)

cleaned = selected.loc[~remove_mask].copy()

removed_noise = initial_selected - len(cleaned)

# =====================================
# 5. Deduplicate exact normalized text
# =====================================

# Case-insensitive exact text deduplication
dedup_key = cleaned["topic_text"].str.casefold()

duplicate_mask = dedup_key.duplicated(keep="first")
duplicate_count = int(duplicate_mask.sum())

final = cleaned.loc[~duplicate_mask].copy()

# =====================================
# 6. Final labels and export
# =====================================

# Preserve the Stage 2 decision for provenance
final = final.rename(
    columns={
        "decision": "stage2_decision",
        "reason": "stage2_reason"
    }
)

# Every row in the final corpus is retained
final["final_decision"] = "KEEP"

final = final.drop(
    columns=["Unnamed: 0", "Duplicate_text_hint"],
    errors="ignore"
)

final.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

# =====================================
# 7. Final statistics
# =====================================

print("\n========== STAGE FINAL ==========")
print(f"Stage 2 original: {len(df):,}")
print(f"Original KEEP: {(df['decision'] == 'KEEP').sum():,}")
print(f"Recovered REVIEW: {recover_review.sum():,}")
print(f"Selected total: {initial_selected:,}")
print(f"Noise removed: {removed_noise:,}")
print(f"Duplicates removed: {duplicate_count:,}")
print("---------------------------------")
print(f"FINAL CORPUS: {len(final):,}")
print(f"Saved to: {OUTPUT}")
print("=================================")
