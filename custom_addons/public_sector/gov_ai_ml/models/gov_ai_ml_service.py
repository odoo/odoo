from odoo import api, models


class GovAiMlService(models.AbstractModel):
    _name = "gov.ai.ml.service"
    _description = "Servico de ML para IA GOV"

    @api.model
    def retrieve_context(self, company_id, query, limit=5):
        Memory = self.env["gov.ai.memory"]
        lexical_records = Memory.search_relevant(company_id, query, limit=max(2, int(limit or 5) * 2))

        lexical_scores = {}
        for index, record in enumerate(lexical_records):
            lexical_scores[record.id] = max(0.0, 1.0 - (index * 0.08))

        vector_scores = {}
        Vector = self.env.get("gov.ai.ml.memory.vector")
        if Vector:
            for memory_id, score in Vector.search_relevant_scored(
                company_id,
                query,
                limit=max(2, int(limit or 5) * 2),
            ):
                vector_scores[memory_id] = float(score)

        merged = {}
        all_ids = set(lexical_scores) | set(vector_scores)
        for memory_id in all_ids:
            merged[memory_id] = (0.55 * lexical_scores.get(memory_id, 0.0)) + (
                0.45 * vector_scores.get(memory_id, 0.0)
            )

        ranked_ids = [memory_id for memory_id, _score in sorted(merged.items(), key=lambda item: item[1], reverse=True)]
        ranked_ids = ranked_ids[: max(1, int(limit or 5))]
        if not ranked_ids:
            return Memory.browse()
        records = Memory.browse(ranked_ids)
        return records.sorted(key=lambda rec: ranked_ids.index(rec.id))

    @api.model
    def log_feedback(self, doc, accepted, score_manual=0, notes="", run=False, template=False):
        if not doc or not doc.exists():
            return False
        company = doc.processo_id.ug_id if doc.processo_id else self.env.company
        template = template or doc.ai_template_id
        run = run or doc.ai_last_run_id
        return self.env["gov.ai.ml.feedback"].create(
            {
                "name": f"Feedback IA - {doc.name or 'Documento'}",
                "company_id": company.id,
                "processo_id": doc.processo_id.id if doc.processo_id else False,
                "doc_id": doc.id,
                "run_id": run.id if run else False,
                "template_id": template.id if template else False,
                "accepted": bool(accepted),
                "score_manual": int(score_manual or 0),
                "notes": notes or "",
            }
        )

    @api.model
    def rank_templates(self, doc, candidate_templates=None, limit=5):
        if not doc or not doc.exists():
            return self.env["gov.ai.template"]
        Feedback = self.env["gov.ai.ml.feedback"]
        domain = [
            ("company_id", "=", doc.processo_id.ug_id.id if doc.processo_id else self.env.company.id),
            ("doc_type", "=", doc.doc_type),
        ]
        if doc.process_type:
            domain.append(("process_type", "=", doc.process_type))
        groups = Feedback.read_group(
            domain,
            fields=["template_id", "id:count"],
            groupby=["template_id"],
            lazy=False,
        )
        weights = {}
        for group in groups:
            template_data = group.get("template_id")
            if not template_data:
                continue
            total = float(group.get("id_count", 0) or 0.0)
            accepted = float(
                Feedback.search_count(
                    (group.get("__domain") or []) + [("accepted", "=", True)]
                )
            )
            if total <= 0:
                continue
            weights[int(template_data[0])] = accepted / total

        templates = candidate_templates or doc.recommended_template_ids
        if not templates:
            templates = self.env["gov.ai.template"].search(
                [
                    ("active", "=", True),
                    ("doc_type", "=", doc.doc_type),
                ]
            )

        ranked_ids = [rec.id for rec in templates.sorted(key=lambda rec: weights.get(rec.id, 0.0), reverse=True)]
        ranked_ids = ranked_ids[: max(1, int(limit or 5))]
        return self.env["gov.ai.template"].browse(ranked_ids)
