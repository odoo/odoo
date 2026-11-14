path = r"custom\school_management\tests\test_academic_transcript_report.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()
bs_quote = chr(92) + chr(34)
text = text.replace(bs_quote, chr(34))
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Replaced all backslash quotes!")
