# Curriculum based on structure from:
# - Gaeilge.ie (official Irish language body)
# - Duolingo Irish team's public CEFR mapping
# - "Buntús Cainte" (foundational Irish language course by RTÉ/Gael Linn)
# - COGG (An Chomhairle um Oideachas Gaeltachta agus Gaelscolaíochta) guidelines

CURRICULUM = [
    {
        "unit": 1,
        "title": "Fáilte — Greetings & Introductions",
        "topics": ["Hello/goodbye", "How are you?", "My name is...", "Where are you from?"],
        "vocab_targets": ["Dia duit", "Slán", "Conas atá tú?", "Is mise...", "Is as... mé"],
        "grammar": "Verb 'Is' (copula) for identity statements",
        "reference": "Buntús Cainte Lesson 1; gaeilge.ie/foghlaim",
    },
    {
        "unit": 2,
        "title": "Uimhreacha — Numbers 1–20",
        "topics": ["Cardinal numbers", "Counting objects", "Age"],
        "vocab_targets": ["a haon–a fiche", "Tá mé... bliain d'aois"],
        "grammar": "Initial mutations after numbers (séimhiú)",
        "reference": "Buntús Cainte Lesson 3; teanglann.ie",
    },
    {
        "unit": 3,
        "title": "An Teaghlach — Family",
        "topics": ["Family members", "Describing your family", "Possessives"],
        "vocab_targets": ["máthair", "athair", "deartháir", "deirfiúr", "mo/do/a"],
        "grammar": "Possessive pronouns + séimhiú",
        "reference": "Gaeilge.ie beginner family unit",
    },
    {
        "unit": 4,
        "title": "Dathanna & Rudaí — Colours & Objects",
        "topics": ["Basic colours", "Classroom objects", "Adjective agreement"],
        "vocab_targets": ["dearg", "gorm", "glas", "bán", "dubh", "leabhar", "peann"],
        "grammar": "Adjective placement after noun; gender agreement",
        "reference": "COGG primary curriculum A1 wordlist",
    },
    {
        "unit": 5,
        "title": "Bia agus Deoch — Food & Drink",
        "topics": ["Common foods", "Ordering", "Likes/dislikes"],
        "vocab_targets": ["arán", "uisce", "tae", "Is maith liom...", "Ní maith liom..."],
        "grammar": "Is maith liom construction (liking)",
        "reference": "Buntús Cainte Lesson 7",
    },
    {
        "unit": 6,
        "title": "An Aimsir — The Weather",
        "topics": ["Weather phrases", "Seasons", "Describing today's weather"],
        "vocab_targets": ["Tá sé fuar", "Tá sé te", "báisteach", "grian", "gaoth"],
        "grammar": "Tá + adjective constructions",
        "reference": "Gaeilge.ie weather unit; rte.ie/brainstorm Irish weather vocabulary",
    },
    {
        "unit": 7,
        "title": "An Chathair — Getting Around Town",
        "topics": ["Places in town", "Directions", "Transport"],
        "vocab_targets": ["sráid", "siopa", "teach", "ar dheis", "ar chlé", "díreach"],
        "grammar": "Prepositions: ar, i, ag, go dtí",
        "reference": "COGG A1-A2 location vocabulary",
    },
    {
        "unit": 8,
        "title": "An Lá — Daily Routine",
        "topics": ["Times of day", "Daily activities", "Present tense verbs"],
        "vocab_targets": ["ar maidin", "iarnóin", "tráthnóna", "éirím", "ithim", "codlaím"],
        "grammar": "Present tense: first conjugation verbs",
        "reference": "Buntús Cainte Lessons 10–11",
    },
]


def get_unit(unit_number: int) -> dict | None:
    for unit in CURRICULUM:
        if unit["unit"] == unit_number:
            return unit
    return None


def format_curriculum_overview() -> str:
    lines = ["📚 *Irish Language Curriculum — Absolute Beginner*\n"]
    for u in CURRICULUM:
        lines.append(f"*Unit {u['unit']}: {u['title']}*")
        lines.append(f"  Grammar: _{u['grammar']}_")
        lines.append(f"  Source: {u['reference']}\n")
    return "\n".join(lines)
