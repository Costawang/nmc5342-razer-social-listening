
import pandas as pd
from pathlib import Path

# 1. 设置数据集路径
folder = Path(r"F:\NMC5342\dataset")

# 2. 自动查找 Brand24 Excel 文件
excel_files = sorted(
    f for f in folder.glob("razer_report*.xlsx")
    if not f.name.startswith("~$")
)

if len(excel_files) != 1:
    raise ValueError(
        f"找到 {len(excel_files)} 个匹配文件，请检查 dataset 文件夹。"
    )

input_file = excel_files[0]
print(f"正在读取：{input_file.name}")

# 3. 读取原始数据
df = pd.read_excel(
    input_file,
    sheet_name="Mentions",
    header=1,
    dtype={"ID": "string"}
)

# 4. 仅保留 Content 非空的记录
mask = df["Content"].astype("string").str.strip().ne("")
df_clean = df.loc[mask.fillna(False)].copy()

# 5. 导出 CSV 到 dataset 文件夹
output_file = folder / "razer_mentions_content_nonempty.csv"

df_clean.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

# 6. 输出统计
print(f"原始数据：{len(df)} 条")
print(f"保留数据：{len(df_clean)} 条")
print(f"删除数据：{len(df) - len(df_clean)} 条")
print(f"保留比例：{len(df_clean) / len(df):.2%}")
print(f"文件已保存：{output_file}")
