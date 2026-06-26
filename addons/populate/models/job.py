from __future__ import annotations

import logging
import math
import time
from ast import literal_eval
from contextlib import contextmanager
from random import Random
from typing import TYPE_CHECKING, Self

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import str2bool

from ..generators import DEFAULT_GENERATORS, Generator, get_fields_vals
from ..utils.orm import VirtualField, drop_pending_update, get_ref_domain
from ..utils.profiling import profiled_execution_scope
from ..utils.seed import derive_seed_from

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from contextlib import AbstractContextManager

MAX_RECORD_COMMIT_SIZE = 1000

_logger = logging.getLogger(__name__)


class Job(models.Model):
    """
    Single unit of work that creates or updates records for one model.

    A job is produced by instantiating a ``populate.blueprint``
    associated with a ``populate.session``. Large jobs are automatically
    split into smaller sub-jobs to allow for more frequent commits,
    preventing excessive memory usage, and enable parallel execution across multiple workers.
    """
    _name = 'populate.job'
    _description = 'Data Population Job'
    _order = 'session_id.id, id ASC'
    _parent_store = True

    seed = fields.Integer()
    parent_id = fields.Many2one('populate.job', index=True)
    child_ids = fields.One2many('populate.job', inverse_name='parent_id')
    parent_path = fields.Char(index=True)
    blueprint_id = fields.Many2one(
        'populate.blueprint',
        related='session_id.blueprint_id',
        store=True,  # avoid joining `populate.session` when searching on `populate.model.data`
        required=True,
        index=True,
        precompute=True,
        ondelete='cascade',
    )
    session_id = fields.Many2one('populate.session', required=True, index=True)
    is_done = fields.Boolean()

    ref = fields.Char(help="""Reference the batch of records used by the job.
    If the job type is 'create' -> Annotates the records for referencing.
    If the job type is 'write' -> Refers to records with said reference.
    """)
    domain = fields.Char(help="Domain selecting target records for jobs that update existing records.")
    model_name = fields.Char(required=True)
    record_count = fields.Integer(default=1)  # Semantics: 0 <-> None
    type = fields.Selection([
        ('create', "Create"),
        ('write', "Write"),
    ], default='create', required=True)
    parallel = fields.Boolean(help="Can the job be executed in parallel?", default=True)
    context = fields.Json()
    instructions = fields.Json()

    _record_count_invariant = models.Constraint(
        "CHECK (record_count > 0 OR (type = 'write' AND record_count = 0))",
        "A job's record_count needs to be a non-zero positive integer. "
        "Only write jobs are allowed to have no record_count, whose cardinality is unknown at creation time.",
    )
    _create_job_without_domain = models.Constraint(
        "CHECK (type != 'create' OR domain IS NULL OR domain = '')",
        "Create jobs cannot define a domain.",
    )
    # partial unique constraint, subjobs copy the info from parents,
    # and you can have multiple write jobs refer the same created records' ref.
    _unique_ref_per_session = models.UniqueIndex(
        "(ref, session_id) WHERE parent_id IS NULL AND type = 'create'",
        "A job with this reference already exists in this session. "
        "References must be unique for create-type jobs within a session.",
    )
    _records_idx = models.Index('(model_name, ref, session_id, blueprint_id)')

    @api.constrains('session_id', 'child_ids', 'parent_id')
    def _check_same_session(self):
        for session, jobs in self.grouped('session_id').items():
            if jobs.parent_id and jobs.parent_id.session_id != session:
                raise ValidationError(self.env._("Jobs in the same hierarchy should share the same session."))

    @api.constrains('child_ids', 'parent_id')
    def _check_parent_hierarchy(self):
        if self._has_cycle():
            raise ValidationError(self.env._("Job hierarchy cannot be recursive."))

    @api.constrains('child_ids', 'parent_id')
    def _check_single_level_hierarchy(self):
        for subjobs in self.filtered('parent_id'):
            if subjobs.parent_id.parent_id:
                raise ValidationError(self.env._(
                    "Subjobs cannot have subjobs themselves. Only one level of hierarchy is allowed.",
                ))

    @property
    def is_executable(self) -> bool:
        """Whether this job performs actual work."""
        return self.parent_id or not self.child_ids

    @property
    def pending_subjobs(self) -> Self:
        return self.child_ids.filtered(lambda job: not job.is_done)

    @property
    def progress(self) -> float:
        """Get the progress of the job as value between [0, 1]"""
        if not self.record_count:
            # For unknown counts -> binary progress.
            return float(self.is_done)

        if self.parent_id:
            done = sum(sibling_job.record_count for sibling_job in self.parent_id.child_ids if sibling_job.is_done)
            total = self.parent_id.record_count
        else:
            if self.is_executable:
                done = self.record_count if self.is_done else 0
            else:
                done = sum(subjob.record_count for subjob in self.child_ids if subjob.is_done)
            total = self.record_count

        return done / total

    def _create_subjobs(self) -> Self:
        """
        Given a job, create the subjobs based on the session, if necessary.
        A subjob, by design, is the same as its parent, it just has a smaller `record_count`,
        based on the sessions `worker_count` and the cap of records that can be committed in one go.
        Their main goal is to allow horizontal scaling and prevent memory issues.
        """
        jobs = self.filtered(lambda j: (
            not j.child_ids      # Already has subjobs, do not recreate them
            and not j.parent_id  # Subjobs cannot have subjobs of their own
            and j.record_count   # Only with a defined record_count can be split.
        ))

        subjob_vals = []
        for job in jobs:
            worker_count = job.session_id.worker_count
            records_to_create = job.record_count

            if records_to_create <= MAX_RECORD_COMMIT_SIZE:
                continue

            max_records_per_worker = min(math.ceil(records_to_create / worker_count), MAX_RECORD_COMMIT_SIZE)
            seed_idx = 0
            while records_to_create > 0:
                batch_size = min(records_to_create, max_records_per_worker)
                vals = job.copy_data(default={
                    'parent_id': job.id,
                    'record_count': batch_size,
                    # Assign a unique seed to each subjob to prevent identical random sequences
                    # when subjobs run in parallel.
                    # Without unique seeds, parallel subjobs would generate identical values,
                    # defeating the purpose of probability distributions and weighted selections,
                    # or violate unique constraints.
                    'seed': derive_seed_from(job.seed, seed_idx),
                })[0]
                subjob_vals.append(vals)
                seed_idx += 1
                records_to_create -= batch_size

        if subjob_vals:
            subjobs = self.env['populate.job'].create(subjob_vals)
            if all_jobs := jobs + subjobs:
                seeds = all_jobs.mapped('seed')
                assert len(seeds) == len(set(seeds)), "All job seeds must be unique"

            return subjobs

        return self.env['populate.job']

    def _execute(self, generators: Mapping[str, Generator] | None = None, *, seed: int | None = None):
        """
        Execute a job.
        If the job has children, execute those, and considers itself done when all children are done
        If the job is a singleton (no parent and no children) or it's a subjob, execute the job itself.

        Side effect: commits transaction when successfully executed.
        """
        self.ensure_one()
        assert not self.is_done, "Cannot execute a job that is already done"
        assert seed is not None or self.seed is not False

        with get_execution_scope(self):
            # A generator's scope is applicable per whole job, subjob included.
            if generators is None:
                generators = self.__create_generators(seed or self.seed)

            if self.is_executable:
                match self.type:
                    case 'create':
                        self._execute_create(generators)
                    case 'write':
                        self._execute_write(generators)
            else:
                for subjob in self.pending_subjobs:
                    subjob._execute(generators, seed=seed)

    def _execute_create(self, generators: Mapping[str, Generator]):
        """Create records for this job and register their populate references.

        :param generators: Field generators keyed by field name.
        """
        self.ensure_one()
        assert self.type == 'create'

        model = self.env[self.model_name]
        records_vals = []

        for _ in range(self.record_count):
            vals = get_fields_vals(generators)
            records_vals.append(vals)

        if context := self.context:
            model = model.with_context(**context)

        new_records = model.create(records_vals)

        self.env['populate.model.data'].create([{
            'res_id': record_id,
            'job_id': self.id,
        } for record_id in new_records.ids])

    def _execute_write(self, generators: Mapping[str, Generator]):
        """Write generated values on the records targeted by this job.

        :param generators: Field generators keyed by field name.
        """
        self.ensure_one()
        assert self.type == 'write'

        domain = self._get_target_domain()

        slice_kwargs = {}
        if self.parent_id:
            preceding_siblings = self.parent_id.child_ids.filtered(lambda job: job.id < self.id)
            slice_kwargs['offset'] = sum(job.record_count for job in preceding_siblings)
            slice_kwargs['limit'] = self.record_count

        records = self.env[self.model_name].with_context(active_test=False).search(domain, **slice_kwargs)

        for record in records:
            vals = get_fields_vals(generators)
            record.write(vals)

    def _get_target_domain(self) -> Domain:
        """Build the ORM domain matching records selected by this job's ``domain`` (+ optional ``ref``)."""
        self.ensure_one()

        domain = Domain(literal_eval(self.domain)) if self.domain else Domain.TRUE
        if self.ref:
            domain &= get_ref_domain(self.env, self.model_name, self.ref, self.session_id, self.blueprint_id)

        return domain

    def __create_generators(self, seed: int) -> Mapping[str, Generator]:
        """Instantiate field generators from the job instructions.

        :param seed: Seed shared by all generators in this job, so generated
            fields remain deterministic relative to each other.
        :return: Generator instances keyed by field name.
        """
        self.ensure_one()
        generators = {}
        model = self.env[self.model_name]
        valid_fields = self.instructions.keys()
        random = Random(seed)
        for field_name, attrs in self.instructions.items():
            if str2bool(attrs.get('virtual', False)):
                field = VirtualField(self.model_name, field_name)
            else:
                field = model._fields[field_name]

            if 'generator' in attrs:
                generator_name = attrs['generator']
            elif 'eval' in attrs:
                generator_name = 'misc.eval'
            elif field.type in DEFAULT_GENERATORS:
                generator_name = DEFAULT_GENERATORS[field.type]
            else:
                raise ValueError(self.env._(
                    "No generator specified for field '%(field)s' of type '%(type)s', "
                    "and no default generator is registered for that field type.",
                    field=field_name,
                    type=field.type,
                ))

            generator = Generator.by_name(generator_name)
            kwargs = {
                'field': field,
                'env': self.env,
                'random': random,
                'job': self,
                'valid_fields': valid_fields,
                **generator.convert_to_kwargs(attrs),
            }
            try:
                generators[field_name] = generator(**kwargs)
            except Exception as exc:
                exc.add_note(self.env._("Generator: '%s'", generator_name))
                exc.add_note(self.env._("Field: '%s'", field))
                if self.ref:
                    exc.add_note(self.env._("Ref: '%s'", self.ref))
                raise

        return generators

    def _log_start(self):
        self.ensure_one()
        progress_info = f'- Session: {self.session_id.progress * 100:.0f}%'
        ref_info = f' [{self.ref}]' if self.ref else ''

        if self.is_executable:
            action = 'Creating' if self.type == 'create' else 'Writing on'
            count = f' {self.record_count}' if self.record_count else ''

            if self.parent_id:
                progress_info = f'- Job: {self.progress * 100:.0f}% ' + progress_info

            _logger.info(
                "Job %(id)s: %(action)s%(count)s %(model)s%(ref)s %(progress)s",
                {
                    'id': self.parent_path[:-1],
                    'action': action,
                    'count': count,
                    'model': self.model_name,
                    'ref': ref_info,
                    'progress': progress_info,
                },
            )
        else:
            assert self.record_count, f"Job {self.parent_path[:-1]} without a known `record_count` couldn't have been split."
            is_parallel = self.parallel and self.session_id.is_parallel
            parallel_info = ' (parallel)' if is_parallel else ''
            _logger.info(
                "Job %(id)s: Planning %(job_count)d subjobs for %(model)s%(ref)s (%(record_count)d records) %(progress)s%(parallel)s",
                {
                    'id': self.id,
                    'job_count': len(self.child_ids),
                    'model': self.model_name,
                    'ref': ref_info,
                    'record_count': self.record_count,
                    'progress': progress_info,
                    'parallel': parallel_info,
                },
            )

    def _log_end(self, elapsed_time):
        self.ensure_one()
        progress_info = f'- Session: {self.session_id.progress * 100:.0f}%'

        if self.parent_id:
            progress_info = f'- Job: {self.progress * 100:.0f}% ' + progress_info

        _logger.info(
            "Job %(id)s: Completed in %(time).2fs %(progress)s",
            {
                'id': self.parent_path[:-1],
                'time': elapsed_time,
                'progress': progress_info,
            },
        )


def get_execution_scope(job: Job) -> AbstractContextManager[Job]:
    """Return the context manager to use for executing one job.

    The plain job scope owns locking, logging, completion, and commit. When
    profiling is enabled, executable jobs are wrapped by the profiler proxy so
    the profiler starts from the caller's ``with`` statement.
    """
    job.ensure_one()

    job_scope = _execution_scope(job)
    if job.session_id.is_profiling:
        return profiled_execution_scope(job, job.session_id.profile_session_name, job_scope)

    return job_scope


@contextmanager
def _execution_scope(job: Job) -> Iterator[Job]:
    """Lock, log, mark done, and commit one job execution.

    :param job: Singleton job being executed.
    :return: Context manager yielding the locked job.
    """
    job.ensure_one()
    job.lock_for_update()  # Shouldn't raise, a locked job -> in progress

    start_time = time.time()
    job._log_start()

    yield job

    if job.is_executable and job.parallel and job.session_id.is_parallel:
        # Discard pending updates to audit log fields (write_uid, write_date) to prevent some
        # serialization errors during data population, where such metadata is not essential.
        drop_pending_update(job.env, ['write_uid', 'write_date'])

    job.is_done = True
    job.env.cr.commit()

    job._log_end(elapsed_time=time.time() - start_time)
