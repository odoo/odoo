from __future__ import annotations
from .object_type import CreativeWork


class HowTo(CreativeWork):
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "estimatedCost": ["MonetaryAmount", "Text"],
        "performTime": "Duration",
        "prepTime": "Duration",
        "step": ['r', "CreativeWork", "HowToSection", "HowToStep", "Text"],
        "supply": ['r', "HowToSupply", "Text"],
        "tool": ['r', "HowToTool", "Text"],
        "totalTime": "Duration",
        "yield": ['r', "QuantitativeValue", "Text"],
    }


class Recipe(HowTo):
    __schema_properties__ = HowTo.__schema_properties__ | {
        "cookTime": "Duration",
        "cookingMethod": ['r', "Text"],
        "nutrition": ['r', "NutritionInformation"],
        "recipeCategory": ['r', "Text"],
        "recipeCuisine": ['r', "Text"],
        "recipeIngredient": ['r', "Text"],
        "recipeInstructions": ['r', "CreativeWork", "ItemList", "Text"],
        "recipeYield": ['r', "QuantitativeValue", "Text"],
        "suitableForDiet": ['r', "RestrictedDiet"]
    }
