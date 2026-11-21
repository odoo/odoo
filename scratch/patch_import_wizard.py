with open("custom/school_public_holiday/wizard/holiday_import_wizard.py", "r", encoding="utf-8") as f:
    content = f.read()

target = '''    def action_confirm_import(self):
        self.ensure_one()
        if not self.preview_line_ids:
            raise UserError(_("No preview lines found. Please upload and preview first."))

        # Check for fatal errors if any
        fatal_lines = self.preview_line_ids.filtered(lambda l: l.status in ("missing_name", "invalid_date"))
        if fatal_lines:
            raise ValidationError(
                _("Cannot proceed with import: %d rows contain invalid dates or missing names. Please fix your file and retry.")
                % len(fatal_lines)
            )

        Holiday = self.env["university.holiday"]
        created_records = Holiday
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        error_msgs = []

        # Create import log first
        log = self.env["school.holiday.import.log"].create({
            "name": self.file_name or _("Public Holidays Import"),
            "duplicate_policy": self.duplicate_policy,
            "total_records": len(self.preview_line_ids),
        })

        try:
            with self.env.cr.savepoint():
                records_to_create = []
                for line in self.preview_line_ids:
                    if line.status == "duplicate":
                        existing = Holiday.search([
                            ("name", "=ilike", line.name),
                            ("date_from", "=", line.date_from),
                        ], limit=1)
                        if self.duplicate_policy == "update" and existing:
                            existing.write({
                                "date_to": line.date_to or line.date_from,
                                "holiday_type": line.holiday_type,
                                "work_pay_multiplier": line.work_pay_multiplier,
                                "note": line.note,
                                "import_batch_id": log.id,
                            })
                            updated_count += 1
                        else:
                            skipped_count += 1
                        continue

                    # Batch creation preparation
                    records_to_create.append({
                        "name": line.name,
                        "date_from": line.date_from,
                        "date_to": line.date_to or line.date_from,
                        "holiday_type": line.holiday_type,
                        "applies_to": "all",
                        "work_pay_multiplier": line.work_pay_multiplier,
                        "note": line.note,
                        "import_batch_id": log.id,
                    })

                # Batch create in chunks of 200 for large files
                BATCH_SIZE = 200
                for i in range(0, len(records_to_create), BATCH_SIZE):
                    batch = records_to_create[i : i + BATCH_SIZE]
                    created_records |= Holiday.create(batch)

        except Exception as exc:
            _logger.exception("Atomic holiday import failure")
            log.write({
                "records_failed": len(self.preview_line_ids),
                "error_log": f"Import failed atomically and was rolled back:\\n{str(exc)}",
            })
            raise ValidationError(
                _("Import aborted atomically due to error: %s\\nNo records were created.") % str(exc)
            )

        # Update log
        log.write({
            "records_created": len(created_records),
            "records_updated": updated_count,
            "records_skipped": skipped_count,
            "records_failed": failed_count,
            "error_log": "\\n".join(error_msgs) if error_msgs else _("Completed cleanly without errors."),
        })

        self.write({
            "state": "done",
            "import_log_id": log.id,
            "summary_msg": _(
                "Import Completed Successfully!\\n"
                "• Created: %d\\n"
                "• Updated: %d\\n"
                "• Skipped: %d\\n"
                "• Total Processed: %d"
            )
            % (len(created_records), updated_count, skipped_count, len(self.preview_line_ids)),
        })'''

replacement = '''    def action_confirm_import(self):
        self.ensure_one()
        if not self.preview_line_ids:
            raise UserError(_("No preview lines found. Please upload and preview first."))

        # Check if all rows are fatal lines (missing name or invalid date)
        fatal_lines = self.preview_line_ids.filtered(lambda l: l.status in ("missing_name", "invalid_date"))
        if fatal_lines and len(fatal_lines) == len(self.preview_line_ids):
            raise ValidationError(
                _("Cannot proceed with import: %d rows contain invalid dates or missing names. Please fix your file and retry.")
                % len(fatal_lines)
            )

        Holiday = self.env["university.holiday"]
        created_records = Holiday
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        error_msgs = []

        # Create import log first
        log = self.env["school.holiday.import.log"].create({
            "name": self.file_name or _("Public Holidays Import"),
            "duplicate_policy": self.duplicate_policy,
            "total_records": len(self.preview_line_ids),
        })

        for line in self.preview_line_ids:
            if line.status in ("missing_name", "invalid_date"):
                failed_count += 1
                error_msgs.append(f"Row {line.line_number}: {line.status_message}")
                continue

            try:
                with self.env.cr.savepoint():
                    if line.status == "duplicate":
                        existing = Holiday.search([
                            ("name", "=ilike", line.name),
                            ("date_from", "=", line.date_from),
                        ], limit=1)
                        if self.duplicate_policy == "update" and existing:
                            existing.write({
                                "date_to": line.date_to or line.date_from,
                                "holiday_type": line.holiday_type,
                                "work_pay_multiplier": line.work_pay_multiplier,
                                "note": line.note,
                                "import_batch_id": log.id,
                            })
                            updated_count += 1
                        else:
                            skipped_count += 1
                        continue

                    # Create row in its own savepoint
                    created = Holiday.create({
                        "name": line.name,
                        "date_from": line.date_from,
                        "date_to": line.date_to or line.date_from,
                        "holiday_type": line.holiday_type,
                        "applies_to": "all",
                        "work_pay_multiplier": line.work_pay_multiplier,
                        "note": line.note,
                        "import_batch_id": log.id,
                    })
                    created_records |= created
            except Exception as exc:
                failed_count += 1
                error_msgs.append(f"Row {line.line_number} ({line.name}): {str(exc)}")

        # Update log
        log.write({
            "records_created": len(created_records),
            "records_updated": updated_count,
            "records_skipped": skipped_count,
            "records_failed": failed_count,
            "error_log": "\\n".join(error_msgs) if error_msgs else _("Completed cleanly without errors."),
        })

        self.write({
            "state": "done",
            "import_log_id": log.id,
            "summary_msg": _(
                "Import Completed Successfully!\\n"
                "• Created: %d\\n"
                "• Updated: %d\\n"
                "• Skipped: %d\\n"
                "• Failed: %d\\n"
                "• Total Processed: %d"
            )
            % (len(created_records), updated_count, skipped_count, failed_count, len(self.preview_line_ids)),
        })'''

assert target in content, "target not found"
new_content = content.replace(target, replacement, 1)
with open("custom/school_public_holiday/wizard/holiday_import_wizard.py", "w", encoding="utf-8") as f:
    f.write(new_content)
print("holiday_import_wizard.py updated successfully")
