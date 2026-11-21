path = r"custom\school_management\tests\test_academic_transcript_report.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace(chr(92) + '"""', '"""')
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Quotes replaced successfully!")
