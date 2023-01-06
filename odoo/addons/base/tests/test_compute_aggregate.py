

import random
import time
import json
import inspect


from odoo import models
from odoo.tests.common import TransactionCase, tagged
from collections import defaultdict
from statistics import NormalDist, fmean, stdev

NB_TIME = 10

@tagged('post_install', '-at_install')
class TestCompute(TransactionCase):

    def all_compute(self, match, file):
        rng = random.Random("a")
        sizes = [1] * NB_TIME + [3] * NB_TIME + [80] * NB_TIME + [1000] * NB_TIME

        res = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for model_name in self.env.registry:
            Model: models.BaseModel = self.env[model_name]
            if Model._abstract or not Model._auto:
                continue

            records = Model.with_context(active_test=False).search([], order='id')
            for field in Model._fields.values():
                if field.store or not field.compute or not records:
                    continue

                func = field.compute
                if isinstance(field.compute, str):
                    func = getattr(records, field.compute)

                source = inspect.getsource(func)
                if match not in source and field.name not in ('qty_available'):
                    continue

                for size in sizes:
                    if size > len(records):
                        continue
                    self.env.invalidate_all()

                    rec = Model.browse(rng.sample(records._ids, size))

                    begin = time.time_ns()
                    res_mapped = rec.mapped(field.name)
                    end = time.time_ns()

                    res[Model._name][field.name][size].append((
                        (end - begin) / 1_000_000,
                        rec._ids,
                        str(res_mapped)
                    ))

        with open(file, 'wt') as fw:
            print(f"Save result {len(res)}")
            json.dump(res, fw)

    def test_all_compute_aggregate(self):
        self.all_compute('aggregate(', 'res_compute_aggregate.json')

    def test_all_compute_read_group(self):
        self.all_compute('read_group(', 'res_compute_read_group.json')

    def test_summarize_result(self):
        files_to_read = [
            'res_compute_read_group.json',
            'res_compute_aggregate.json',
        ]

        all_results = []
        for file in files_to_read:
            with open(file, 'rt') as fw:
                all_results.append(json.load(fw))

        def x_bests(values):
            return sorted(values)[:5]

        def statically_faster(values_1, values_2):
            """ Return true if values_1 is statically less than values_2 for a normal distrubion
            """
            n1 = NormalDist.from_samples(values_1)
            n2 = NormalDist.from_samples(values_2)
            p = n1.overlap(n2)
            return p < 0.05 and fmean(values_1) < fmean(values_2)

        WHITE = '\033[37m'
        RED = '\033[31m'
        GREEN = '\033[32m'
        RESET = '\033[0m'

        issues = []

        base_res = all_results[0]
        for model_name, res_model in base_res.items():
            for field_name, res_field in res_model.items():
                print(f"For {model_name}..{field_name}:")
                for size, res_size in res_field.items():
                    base_sample, base_rec, base_compute_res = zip(*res_size)
                    base_sample = x_bests(base_sample)
                    result = [f"{fmean(base_sample):>8.2f} -+ {stdev(base_sample):.2f}"]  # List of string

                    for one_res in all_results[1:]:
                        if model_name not in one_res or field_name not in one_res[model_name]:
                            result.append('no_data')
                            continue
                        one_res = one_res[model_name][field_name][size]
                        one_sample, one_rec, one_compute_res = zip(*one_res)
                        one_sample = x_bests(one_sample)
                        color = WHITE
                        if statically_faster(one_sample, base_sample):
                            color = GREEN
                        elif statically_faster(base_sample, one_sample):
                            color = RED

                        result.append(f"{color}{fmean(one_sample):>7.2f}{RESET} -+ {stdev(one_sample):.2f}")
                        if size == "1":
                            if base_rec != one_rec:
                                issues.append(f"{model_name}..{field_name}: records {base_rec} != {one_rec}")
                            if base_compute_res != one_compute_res and base_rec == one_rec:
                                issues.append(f"{model_name}..{field_name}: values {base_compute_res} != {one_compute_res} for {one_rec}")

                    print(f"\t- {int(size):4}: " + ' | '.join(result) + " ms")

        print("\n".join(issues))