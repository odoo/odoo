# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import reprlib

shortener = reprlib.Repr()
shortener.maxstring = 150
shorten = shortener.repr


class Speedscope:
    def __init__(self, name='Speedscope', init_stack_trace=None):
        self.init_stack_trace = init_stack_trace or []
        self.init_stack_trace_level = len(self.init_stack_trace)
        self.caller_frame = None
        self.convert_stack(self.init_stack_trace)

        self.init_caller_frame = None
        if self.init_stack_trace:
            self.init_caller_frame = self.init_stack_trace[-1]
        self.profiles_raw = {}
        self.name = name
        self.frames_indexes = {}
        self.frame_count = 0
        self.profiles = []

    def add(self, key, profile):
        for entry in profile:
            self.caller_frame = self.init_caller_frame
            self.convert_stack(entry['stack'] or [])
            if 'query' in entry:
                query = entry['query']
                full_query = entry['full_query']
                entry['stack'].append((f'sql({shorten(query)})', full_query, None))
        self.profiles_raw[key] = profile

    def convert_stack(self, stack):
        for index, frame in enumerate(stack):
            method = frame[2]
            line = ''
            number = ''
            if self.caller_frame and len(self.caller_frame) == 4:
                line = f"called at {self.caller_frame[0]} ({self.caller_frame[3].strip()})"
                number = self.caller_frame[1]
            stack[index] = (method, line, number,)
            self.caller_frame = frame

    def add_output(self, names, complete=True, display_name=None, use_context=True, **params):
        entries = []
        display_name = display_name or ','.join(names)
        for name in names:
            entries += self.profiles_raw[name]
        entries.sort(key=lambda e: e['start'])
        result = self.process(entries, use_context=use_context, **params)
        if not result:
            return self
        start = result[0]['at']
        end = result[-1]['at']

        if complete:
            start_stack = []
            end_stack = []
            init_stack_trace_ids = self.stack_to_ids(self.init_stack_trace, use_context and entries[0].get('exec_context'))
            for frame_id in init_stack_trace_ids:
                start_stack.append({
                    "type": "O",
                    "frame": frame_id,
                    "at": start
                })
            for frame_id in reversed(init_stack_trace_ids):
                end_stack.append({
                    "type": "C",
                    "frame": frame_id,
                    "at": end
                })
            result = start_stack + result + end_stack

        self.profiles.append({
            "name": display_name,
            "type": "evented",
            "unit": "seconds",
            "startValue": 0,
            "endValue": end - start,
            "events": result
        })
        return self

    def add_default(self):
        if len(self.profiles_raw) > 1:
            self.add_output(self.profiles_raw, display_name='Combined')
            self.add_output(self.profiles_raw, display_name='Combined no context', use_context=False)
        for key, profile in self.profiles_raw.items():
            sql = profile and profile[0].get('query')
            if sql:
                self.add_output([key], hide_gaps=True, display_name=f'{key} (no gap)')
                self.add_output([key], continuous=False, complete=False, display_name=f'{key} (density)')

            else:
                self.add_output([key], display_name=key)
        return self

    def make(self):
        if not self.profiles:
            self.add_default()
        return {
            "name": self.name,
            "activeProfileIndex": 0,
            "$schema": "https://www.speedscope.app/file-format-schema.json",
            "shared": {
                "frames": [{
                    "name": frame[0],
                    "file": frame[1],
                    "line": frame[2]
                } for frame in self.frames_indexes]
            },
            "profiles": self.profiles,
        }

    def get_frame_id(self, frame):
        if frame not in self.frames_indexes:
            self.frames_indexes[frame] = self.frame_count
            self.frame_count += 1
        return self.frames_indexes[frame]

    def stack_to_ids(self, stack, context, stack_offset=0):
        """
            :param stack: A list of hashable frame
            :param context: an iterable of (level, value) ordered by level
            :param stack_offset: offset level for stack

            Assemble stack and context and return a list of ids representing
            this stack, adding each corresponding context at the corresponding
            level.
        """
        stack_ids = []
        context_iterator = iter(context or ())
        context_level, context_value = next(context_iterator, (None, None))
        # consume iterator until we are over stack_offset
        while context_level is not None and context_level < stack_offset:
            context_level, context_value = next(context_iterator, (None, None))
        for level, frame in enumerate(stack, start=stack_offset + 1):
            while context_level == level:
                context_frame = (", ".join(f"{k}={v}" for k, v in context_value.items()), '', '')
                stack_ids.append(self.get_frame_id(context_frame))
                context_level, context_value = next(context_iterator, (None, None))
            stack_ids.append(self.get_frame_id(frame))
        return stack_ids

    def process(self, entries, continuous=True, hide_gaps=False, use_context=True, constant_time=False):
        # constant_time parameters is mainly useful to hide temporality when focussing on sql determinism
        entry_end = previous_end = None
        if not entries:
            return []
        events = []
        current_stack_ids = []
        frames_start = entries[0]['start']

        # add last closing entry if missing
        last_entry = entries[-1]
        if last_entry['stack']:
            entries.append({'stack': [], 'start': last_entry['start'] + last_entry.get('time', 0)})

        for index, entry in enumerate(entries):
            if constant_time:
                entry_start = close_time = index
            else:
                previous_end = entry_end

                if hide_gaps and previous_end:
                    entry_start = previous_end
                else:
                    entry_start = entry['start'] - frames_start

                if previous_end and previous_end > entry_start:
                    # skip entry if entry starts after another entry end
                    continue

                if previous_end:
                    close_time = min(entry_start, previous_end)
                else:
                    close_time = entry_start

                entry_time = entry.get('time')
                entry_end = None if entry_time is None else entry_start + entry_time

            entry_stack_ids = self.stack_to_ids(
                entry['stack'] or [],
                use_context and entry.get('exec_context'),
                self.init_stack_trace_level
            )
            level = 0
            if continuous:
                level = -1
                for level, at_level in enumerate(zip(current_stack_ids, entry_stack_ids)):
                    current, new = at_level
                    if current != new:
                        break
                else:
                    level += 1

            for frame in reversed(current_stack_ids[level:]):
                events.append({
                    "type": "C",
                    "frame": frame,
                    "at": close_time
                })
            for frame in entry_stack_ids[level:]:
                events.append({
                    "type": "O",
                    "frame": frame,
                    "at": entry_start
                })
            current_stack_ids = entry_stack_ids

        return events
