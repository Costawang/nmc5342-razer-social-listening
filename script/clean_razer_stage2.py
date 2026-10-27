
import re
import html
from pathlib import Path
import pandas as pd

# ==============================
# 1. Paths and input
# ==============================

ROOT = Path(r"F:\NMC5342")
INPUT = ROOT / "dataset" / "razer_mentions_content_nonempty.csv"
OUT = ROOT / "dataset" / "stage2"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    INPUT,
    encoding="utf-8-sig",
    dtype={"ID": "string"},
    low_memory=False
)

for col in ["Content", "Title", "Domain", "Category"]:
    df[col] = df[col].fillna("").astype(str)

# ==============================
# 2. Clean text without modifying original Content
# ==============================

def clean_text(text):
    text = html.unescape(text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = text.replace("[...]", " ")
    return re.sub(r"\s+", " ", text).strip()

df["Content_clean"] = df["Content"].map(clean_text)

# Diagnostic flags
df["Truncated_hint"] = df["Content"].str.len().ge(249)
df["Duplicate_text_hint"] = df.duplicated(
    ["Domain", "Title", "Content"],
    keep="first"
)

df["decision"] = "KEEP"
df["reason"] = "organic_candidate"

domain = df["Domain"].str.strip().str.lower()
category = df["Category"].str.strip().str.lower()
body = df["Content"].str.lower()
title = df["Title"].str.lower()

def assign(condition, decision, reason):
    mask = condition & df["decision"].eq("KEEP")
    df.loc[mask, ["decision", "reason"]] = [decision, reason]

# ==============================
# 3. High-confidence exclusions
# ==============================

# Twitch stream metadata, not user comments
assign(
    domain.eq("twitch.tv"),
    "EXCLUDE",
    "twitch_stream_metadata"
)

# Repeated Telegram gift-card advertising
telegram_spam = (
    domain.eq("t.me")
    & (
        title.eq("fbadsbh")
        | (
            body.str.contains(r"gift\s*cards?", regex=True)
            & body.str.contains(
                r"cash|bank|buy|sell|amazon|steam|nike|vanilla",
                regex=True
            )
        )
    )
)

assign(
    telegram_spam,
    "EXCLUDE",
    "telegram_mass_giftcard_ads"
)

# Merchant catalog pages
assign(
    domain.isin([
        "startselect.com",
        "amazon.com",
        "amazon.in",
        "mobiletopup.co.uk"
    ]),
    "EXCLUDE",
    "merchant_product_pages"
)

# Job advertisements
job_mask = (
    domain.eq("sportstechjobs.com")
    | body.str.contains(
        "joining razer will place you on a global mission",
        regex=False
    )
    | (
        body.str.contains(
            r"#jobalert|#jobsearch|\bis\s+#hiring\b",
            regex=True
        )
        & body.str.contains("razer", regex=False)
    )
)

assign(job_mask, "EXCLUDE", "recruitment_listing")

# ==============================
# 4. Separate contextual data
# ==============================

# News/web/blogs are not necessarily consumer comments.
# Keep Razer Insider as a community-source exception.
assign(
    category.isin(["news", "web", "blogs", "podcasts"])
    & ~domain.eq("insider.razer.com"),
    "CONTEXT",
    "news_blog_or_web_source"
)

# YouTube video descriptions are not comments
assign(
    domain.eq("youtube.com"),
    "CONTEXT",
    "youtube_video_description_not_comment"
)

# Official brand posts should be analyzed separately
assign(
    domain.eq("tiktok.com")
    & title.isin([
        "razer",
        "razerstore",
        "razeruk",
        "razerphilippines",
        "razerph"
    ]),
    "CONTEXT",
    "official_brand_content"
)

# ==============================
# 5. Flag uncertain records for human review
# ==============================

# Possible affiliate/deal bot
assign(
    domain.eq("bsky.app")
    & body.str.contains(
        r"shop now|buy now|lowest price|"
        r"\breg\s*\$|\btag=\S+|\b\d+% off\b",
        regex=True
    ),
    "REVIEW",
    "possible_affiliate_or_deal_bot"
)

# News reposting accounts
assign(
    domain.eq("bsky.app")
    & title.str.contains(
        r"\.(?:com|net|org|be)$",
        regex=True
    ),
    "REVIEW",
    "possible_news_repost"
)

# Resale or marketplace posts
assign(
    domain.eq("reddit.com")
    & title.str.contains(
        r"\[(?:WTS|WTB|USA|US-)|"
        r"\bselling\b|\bfor sale\b|\bwant to sale\b",
        regex=True
    ),
    "REVIEW",
    "resale_or_listing"
)

# Sponsored TikTok content
assign(
    domain.eq("tiktok.com")
    & body.str.contains(
        r"(?<!\w)#ad\b|\baffiliate\b|"
        r"\blink in bio\b|\bshop now\b",
        regex=True
    ),
    "REVIEW",
    "sponsored_or_store_caption"
)

# Other Telegram content
assign(
    domain.eq("t.me"),
    "REVIEW",
    "other_telegram_content"
)

# No visible Razer mention:
# Review only, because Brand24 excerpts may be truncated.
brand_context = (
    df["Content"].str.contains(
        r"\brazer\b", case=False, regex=True
    )
    | df["Title"].str.contains(
        r"\brazer\b", case=False, regex=True
    )
)

assign(
    ~brand_context,
    "REVIEW",
    "no_razer_in_visible_title_or_text"
)

# Very short texts need context
assign(
    df["Content_clean"].str.len().lt(20),
    "REVIEW",
    "too_short_for_context"
)

# ==============================
# 6. Export all results
# ==============================

df.to_csv(
    OUT / "razer_stage2_all_with_labels.csv",
    index=False,
    encoding="utf-8-sig"
)

files = {
    "KEEP": "razer_stage2_core.csv",
    "REVIEW": "razer_stage2_manual_review.csv",
    "CONTEXT": "razer_stage2_context.csv",
    "EXCLUDE": "razer_stage2_excluded.csv"
}

for status, filename in files.items():
    subset = df[df["decision"] == status]
    subset.to_csv(
        OUT / filename,
        index=False,
        encoding="utf-8-sig"
    )

# ==============================
# 7. Summary
# ==============================

print("\n=== RAZER STAGE 2 SUMMARY ===")
print("Original:", len(df))
print(df["decision"].value_counts())
print("\nDecision reasons:")
print(df.groupby(["decision", "reason"]).size())
print("\nPotential duplicate texts:",
      df["Duplicate_text_hint"].sum())
print("\nOutput:", OUT)
