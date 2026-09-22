import unicodedata


def fold(text):
    plain = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in plain if not unicodedata.combining(ch)).lower().strip()


def match_person(known, guess):
    guess = fold(guess)
    if not guess:
        return None
    folded = {fold(name): person for name, person in known.items()}
    if guess in folded:
        return folded[guess]
    hits = [
        person
        for name, person in folded.items()
        if name
        and (guess in name or name in guess or guess.split()[0] == name.split()[0])
    ]
    return hits[0] if len(hits) == 1 else None
