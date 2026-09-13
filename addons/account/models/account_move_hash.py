from hashlib import sha256
from json import dumps

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_repr

from .account_move import MAX_HASH_VERSION
from .account_move import AccountMove as AccountMoveMain

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_fields_integrity_hash(self):
        hash_version = self.env.context.get("hash_version", MAX_HASH_VERSION)
        if hash_version == 1:
            return ["date", "journal_id", "company_id"]
        elif hash_version in (2, 3, 4):
            return ["name", "date", "journal_id", "company_id"]
        raise NotImplementedError(f"hash_version={hash_version} doesn't exist")

    def _get_integrity_hash_fields_and_subfields(self):
        return self._get_fields_integrity_hash() + [
            f"line_ids.{subfield}"
            for subfield in self.line_ids._get_fields_integrity_hash()
        ]

    @api.model
    def _get_domain_move_hash(self, common_domain=False, force_hash=False):
        domain = Domain(common_domain or Domain.TRUE) & Domain("state", "=", "posted")
        if force_hash:
            return domain
        return domain & Domain("restrict_mode_hash_table", "=", True)

    @api.model
    def _is_move_restricted(self, move, force_hash=False):
        return move.filtered_domain(self._get_domain_move_hash(force_hash=force_hash))

    def _hash_moves(self, **kwargs):
        chains_to_hash = self._get_chains_to_hash(**kwargs)
        grant_secure_group_access = False
        _debug.pipeline(
            "_hash_moves", records=self, chains_to_hash_count=len(chains_to_hash)
        )
        for chain in chains_to_hash:
            _debug.pipeline(
                "hashing_chain",
                moves=chain["moves"],
                restrict_mode=chain["journal_restrict_mode"],
                warnings=chain.get("warnings"),
            )
            move_hashes = chain["moves"].sudo()._get_hashes(chain["previous_hash"])
            for move, move_hash in move_hashes.items():
                super(AccountMoveMain, move).write({"inalterable_hash": move_hash})
            if not chain["journal_restrict_mode"]:
                grant_secure_group_access = True
            chain["moves"]._message_log_batch(
                bodies={
                    m.id: self.env._("This journal entry has been secured.")
                    for m in chain["moves"]
                }
            )
        if grant_secure_group_access:
            self.env["res.groups"]._activate_group_account_secured()

    def _get_domain_chain_hash(
        self, last_move_in_chain, last_move_hashed, common_domain, include_pre_last_hash
    ):
        domain = self.env["account.move"]._get_domain_move_hash(
            [
                *common_domain,
                ("sequence_number", "<=", last_move_in_chain.sequence_number),
                ("inalterable_hash", "=", False),
            ],
            force_hash=True,
        )
        if last_move_hashed and not include_pre_last_hash:
            domain &= Domain("sequence_number", ">", last_move_hashed.sequence_number)
        return domain

    def _get_chain_warnings(
        self, moves_to_hash, last_move_hashed, include_pre_last_hash
    ):
        warnings = set()
        if not moves_to_hash:
            warnings.add("no_document")
            _debug.logic("chain_empty", last_move=last_move_hashed)
            return warnings

        seq_numbers = moves_to_hash.mapped("sequence_number")
        if last_move_hashed and not include_pre_last_hash:
            start = last_move_hashed.sequence_number + 1
        else:
            start = seq_numbers[0]
        if seq_numbers != list(range(start, seq_numbers[-1] + 1)):
            warnings.add("gap")

        has_unreconciled = bool(
            self.env["account.bank.statement.line"].search_count(
                [
                    ("move_id", "in", moves_to_hash.ids),
                    ("is_reconciled", "=", False),
                ],
                limit=1,
            )
        )
        if has_unreconciled:
            warnings.add("unreconciled")
        _debug.logic(
            "chain_warnings_collected",
            moves=moves_to_hash,
            last_move=last_move_hashed,
            start=start,
            warnings=warnings,
        )
        return warnings

    @_debug.perf.timed
    def _get_chain_info(
        self, force_hash=False, include_pre_last_hash=False, early_stop=False
    ):
        if not self:
            return False

        last_move_in_chain = (
            self.env["account.move"]
            .sudo()
            .search_fetch(
                domain=[("id", "in", self.ids)],
                field_names=[
                    "sequence_prefix",
                    "sequence_number",
                    "journal_id",
                    "state",
                    "restrict_mode_hash_table",
                ],
                order="sequence_number desc",
                limit=1,
            )
        )
        journal = last_move_in_chain.journal_id
        if not self._is_move_restricted(last_move_in_chain, force_hash=force_hash):
            _debug.logic(
                "chain_not_restricted_no_hashing",
                journal=journal,
                sequence_prefix=last_move_in_chain.sequence_prefix,
                force=force_hash,
            )
            return False

        common_domain = [
            ("journal_id", "=", journal.id),
            ("sequence_prefix", "=", last_move_in_chain.sequence_prefix),
        ]
        last_move_hashed = (
            self.env["account.move"]
            .sudo()
            .search_fetch(
                [
                    *common_domain,
                    ("inalterable_hash", "!=", False),
                ],
                ["sequence_number", "inalterable_hash"],
                order="sequence_number desc",
                limit=1,
            )
        )

        domain = self._get_domain_chain_hash(
            last_move_in_chain,
            last_move_hashed,
            common_domain,
            include_pre_last_hash,
        )
        if early_stop:
            return self.env["account.move"].sudo().search_count(domain, limit=1)
        moves_to_hash = (
            self.env["account.move"]
            .sudo()
            .search_fetch(domain, ["sequence_number"], order="sequence_number")
        )
        info = {
            "previous_hash": last_move_hashed.inalterable_hash,
            "last_move_hashed": last_move_hashed,
        }
        if self.env.context.get("chain_info_warnings", True):
            info["warnings"] = self._get_chain_warnings(
                moves_to_hash, last_move_hashed, include_pre_last_hash
            )

        moves = moves_to_hash.sudo(False)
        _debug.logic(
            "chain_last_hashed_hash",
            journal=journal,
            sequence_prefix=last_move_in_chain.sequence_prefix,
            sequence_number=last_move_hashed.sequence_number,
            moves_to_hash_count=len(moves_to_hash),
            warnings=info.get("warnings"),
        )
        info.update(
            {
                "moves": moves,
                "remaining_moves": self - moves,
            }
        )
        return info

    @_debug.perf.timed
    def _get_chains_to_hash(
        self,
        force_hash=False,
        raise_if_gap=True,
        raise_if_no_document=True,
        raise_if_unreconciled=True,
        include_pre_last_hash=False,
        early_stop=False,
    ):
        res = []
        for journal, journal_moves in self.grouped("journal_id").items():
            for chain_moves in journal_moves.grouped("sequence_prefix").values():
                chain_info = chain_moves._get_chain_info(
                    force_hash=force_hash,
                    include_pre_last_hash=include_pre_last_hash,
                    early_stop=early_stop,
                )

                if not chain_info:
                    _debug.logic(
                        "nothing_hash", journal=journal, chain_moves=chain_moves
                    )
                    continue
                if early_stop:
                    return True
                chain_info["journal_restrict_mode"] = journal.restrict_mode_hash_table

                warnings = chain_info.get("warnings") or set()
                if raise_if_unreconciled and "unreconciled" in warnings:
                    raise UserError(
                        _(
                            "An error occurred when computing the inalterability. All entries have to be reconciled."
                        )
                    )

                if raise_if_no_document and "no_document" in warnings:
                    raise UserError(
                        _(
                            "This move could not be locked either because "
                            "some move with the same sequence prefix has a higher number. You may need to resequence it."
                        )
                    )
                if raise_if_gap and "gap" in warnings:
                    raise UserError(
                        _(
                            "An error occurred when computing the inalterability. A gap has been detected in the sequence."
                        )
                    )

                res.append(chain_info)
        if early_stop:
            return False
        return res

    @_debug.perf.timed
    def _get_hashes(self, previous_hash):
        hash_version = self.env.context.get("hash_version", MAX_HASH_VERSION)

        def get_field_as_string(obj, field_name):
            field_value = obj[field_name]
            if obj._fields[field_name].type == "many2one":
                field_value = field_value.id
            if obj._fields[field_name].type == "monetary" and hash_version >= 3:
                return float_repr(field_value, obj.currency_id.decimal_places)
            return str(field_value)

        move2hash = {}
        previous_hash = previous_hash or ""
        _debug.pipeline(
            "hash_chain_start",
            moves=self,
            hash_version=hash_version,
            chained=bool(previous_hash),
        )

        for move in self:
            if previous_hash and previous_hash.startswith("$"):
                previous_hash = previous_hash.split("$")[2]
            values = {}
            for fname in move._get_fields_integrity_hash():
                values[fname] = get_field_as_string(move, fname)

            for line in move.line_ids:
                for fname in line._get_fields_integrity_hash():
                    k = "line_%d_%s" % (line.id, fname)
                    values[k] = get_field_as_string(line, fname)
            current_record = dumps(
                values,
                sort_keys=True,
                ensure_ascii=True,
                indent=None,
                separators=(",", ":"),
            )
            hash_string = sha256(
                (previous_hash + current_record).encode("utf-8")
            ).hexdigest()
            move2hash[move] = (
                f"${hash_version}${hash_string}" if hash_version >= 4 else hash_string
            )
            previous_hash = move2hash[move]
        _debug.pipeline(
            "hashes_computed",
            moves=self,
            count=len(move2hash),
            hash_version=hash_version,
        )
        return move2hash
