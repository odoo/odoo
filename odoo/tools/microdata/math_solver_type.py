from __future__ import annotations
from enum import Enum
from .core.learning_resource_type import LearningResource
from .core.object_type import (
    URL, CreativeWork
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.action_type import SolveMathAction


class ProblemType(Enum):
    AbsoluteValueEquation = "Absolute Value Equation"
    Algebra = "Algebra"
    ArcLength = "Arc Length"
    Arithmetic = "Arithmetic"
    BiquadraticEquation = "Biquadratic Equation"
    Calculus = "Calculus"
    CharacteristicPolynomial = "Characteristic Polynomial"
    Circle = "Circle"
    Derivative = "Derivative"
    DifferentialEquation = "Differential Equation"
    Distance = "Distance"
    Eigenvalue = "Eigenvalue"
    Eigenvector = "Eigenvector"
    Ellipse = "Ellipse"
    ExponentialEquation = "Exponential Equation"
    Function = "Function"
    FunctionComposition = "Function Composition"
    Geometry = "Geometry"
    Hyperbola = "Hyperbola"
    InflectionPoint = "Inflection Point"
    Integral = "Integral"
    Intercept = "Intercept"
    Limit = "Limit"
    LineEquation = "Line Equation"
    LinearAlgebra = "Linear Algebra"
    LinearEquation = "Linear Equation"
    LinearInequality = "Linear Inequality"
    LogarithmicEquation = "Logarithmic Equation"
    LogarithmicInequality = "Logarithmic Inequality"
    Matrix = "Matrix"
    Midpoint = "Midpoint"
    Parabola = "Parabola"
    Parallel = "Parallel"
    Perpendicular = "Perpendicular"
    PolynomialEquation = "Polynomial Equation"
    PolynomialExpression = "Polynomial Expression"
    PolynomialInequality = "Polynomial Inequality"
    QuadraticEquation = "Quadratic Equation"
    QuadraticExpression = "Quadratic Expression"
    QuadraticInequality = "Quadratic Inequality"
    RadicalEquation = "Radical Equation"
    RadicalInequality = "Radical Inequality"
    RationalEquation = "Rational Equation"
    RationalExpression = "Rational Expression"
    RationalInequality = "Rational Inequality"
    Slope = "Slope"
    Statistics = "Statistics"
    SystemOfEquations = "System of Equations"
    Trigonometry = "Trigonometry"


class MathSolver(CreativeWork):
    __description__ = """
        A math solver which is capable of solving a subset of mathematical
        problems.
    """
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "mathExpression": ["SolveMathAction", "Text"]
    }

    def __init__(self,
                 math_expression: SolveMathAction | str | None = None,
                 **kwargs) -> None:
        super().__init__(math_expression=math_expression, **kwargs)


class LearningMathSolver(MathSolver, LearningResource):
    __description__ = """
        Google specific type
        A math solver which is capable of solving a subset of mathematical
        problems.
    """
    __schema_properties__ = MathSolver.__schema_properties__ | LearningResource.__schema_properties__
    __type_name__ = ["MathSolver", "LearningResource"]

    def __init__(self,
                 potential_action: SolveMathAction | list[SolveMathAction],
                 url: URL | str,
                 usage_info: URL | str,
                 in_language: str | None = None,
                 assesses: str | ProblemType | list[str | ProblemType] | None = None,
                 **kwargs) -> None:
        super().__init__(
            potential_action=potential_action,
            url=url,
            usage_info=usage_info,
            in_language=in_language,
            assesses=assesses,
            **kwargs
        )
