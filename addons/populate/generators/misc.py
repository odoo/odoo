from itertools import count, cycle

from odoo import Command
from odoo.tools.safe_eval import safe_eval

from ..utils.expression import check_eval_kwargs, get_undefined_names
from .generator import Generator


class Counter(Generator):
    """
    Generate values from an arithmetic sequence, similar to Python's ``range()``.

    Produces values starting at ``start``, incrementing by ``step`` each time.
    If ``end`` is provided, the sequence wraps around (like ``misc.cycle``) once
    the boundary is reached. Without ``end``, the counter runs indefinitely.
    """
    name = 'misc.counter'
    allowed_field_types = ('integer', 'float', 'virtual')

    def __init__(self, start: float = 0, step: float = 1, end: float | None = None, **kwargs):
        """Initialize the arithmetic sequence.

        :param start: First generated value.
        :param step: Increment applied after each generated value.
        :param end: Exclusive boundary that makes the sequence wrap around.
        """
        super().__init__(**kwargs)

        if step == 0:
            raise ValueError(self.env._(
                "Step cannot be zero for the counter generator. Use `eval` with a static value instead.",
            ))

        if start.is_integer():
            start = int(start)

        if step.is_integer():
            step = int(step)

        if end is not None:
            if step > 0 and end <= start:
                raise ValueError(self.env._(
                    "When step is positive, end (%(end)s) must be greater than start (%(start)s).",
                    end=end, start=start,
                ))
            if step < 0 and end >= start:
                raise ValueError(self.env._(
                    "When step is negative, end (%(end)s) must be less than start (%(start)s).",
                    end=end, start=start,
                ))
            if end.is_integer():
                end = int(end)

        self.null_ratio = 0

        # When we need to generate a globally unique sequence in multi-worker mode,
        # we split the sequence into distinct strides to avoid a de-facto serialization,
        # that would happen from the `unique` value retry mechanism.
        if self.unique and self.job and self.job.parent_id and self.job.session_id.is_parallel:
            sibling_ids = self.job.parent_id.child_ids.ids
            sibling_index = sibling_ids.index(self.job.id)
            start += step * sibling_index
            step *= len(sibling_ids)

        self.counter = (
            cycle(range(start, end, step))
            if end is not None
            else count(start, step)
        )

    def _next(self, known_vals):
        return next(self.counter)

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)
        kwargs.update(**{k: float(v) for k, v in attrs.items() if k in ('start', 'step', 'end')})
        return kwargs


class Cycle(Generator):
    """Deterministically cycle through a list of values in order."""
    name = 'misc.cycle'
    allowed_field_types = ('integer', 'float', 'char', 'text', 'html', 'date', 'datetime', 'virtual')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not self.values:
            raise ValueError(self.env._("Values cannot be empty for the cycle generator."))

        if self.has_weights:
            raise ValueError(self.env._("Weights cannot be provided for the cycle generator."))

        # The cycle generator cycles through values deterministically in order.
        # To prevent unintended False/None values, null_ratio is set to 0.
        # If False/None values are needed, they should be explicitly included in the values list.
        self.null_ratio = 0
        self.cycle = cycle(self.values)

    def _next(self, known_vals):
        return next(self.cycle)


class Eval(Generator):
    """Evaluate a Python expression, optionally depending on other fields."""
    name = 'misc.eval'

    def __init__(self, expr: str, **kwargs):
        """Compile a safe-eval expression and infer its field dependencies.

        :param expr: Python expression from the blueprint ``eval`` attribute.
        """
        env = kwargs['env']

        if expr.strip().startswith('lambda'):
            raise ValueError(env._(
                "The eval generator takes an expression directly instead of a lambda. "
                "Use 'x + y' instead of 'lambda x, y: x + y'.",
            ))

        required_names = get_undefined_names(expr)
        eval_ctx = self._get_eval_context(**kwargs)
        depends = list(required_names - set(eval_ctx.keys())) if required_names else None

        super().__init__(depends=depends, **kwargs)

        # Store the original expression for clear error reporting
        self.expr = expr

        # Only the result of the evaluation should be a possible output value.
        self.null_ratio = 0

        if self.depends:
            # it's a raw expression that has dependencies,
            # wrap it into a lambda that takes the depends as args.
            args = ', '.join(self.depends)
            expr = f'lambda {args}: {expr}'
        elif self.unique:
            raise ValueError(self.env._("This Eval returns the same value, so it cannot be unique."))

        evaluation = safe_eval(expr, context=eval_ctx)

        if callable(evaluation):
            def checked(**eval_kwargs):
                check_eval_kwargs(eval_kwargs)
                return evaluation(**eval_kwargs)

            self.evaluation = checked
        else:
            self.evaluation = evaluation

    def _next(self, known_vals):
        if not callable(self.evaluation):
            return self.evaluation

        kwargs = {dep: known_vals[dep] for dep in self.depends}
        try:
            return self.evaluation(**kwargs)
        except Exception as e:  # noqa: BLE001
            e.add_note(f"Expression: '{self.expr}'")
            raise

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)

        if 'eval' in attrs:
            kwargs['expr'] = attrs['eval']

        return kwargs

    def _get_eval_context(self, **kwargs):
        env = getattr(self, 'env', kwargs['env'])
        field = getattr(self, 'field', kwargs['field'])
        return {
            'env': env,
            'model': env[field.model_name],
            'Command': Command,
        }
