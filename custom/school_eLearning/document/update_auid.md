# Update: Class Section eLearning Integration

## Scope

`models/class_section.py` extends `university.class.section` with access to the
eLearning courses linked to that class section.

## Current behavior

- `slide_channel_ids` provides the inverse relation to `slide.channel.class_section_id`.
- `slide_channel_count` computes the number of linked courses for the section.
- `action_view_slide_channels()` opens the eLearning course overview filtered to the
  current section and supplies defaults for the section, its subject, and its assigned
  teacher when available.
- `views/class_section_views.xml` exposes this action and count as a stat button.
- Courses use `slide_channel_ids` as the canonical inverse relation; do not add a
  separate course relation that can become inconsistent.
- Selecting a class section on a course sets its subject and defaults its teacher.
  Changing the course subject clears a class section assigned to a different subject.
- Course access is aligned with school roles: administrators have full access,
  teachers can manage courses, and HOD/dean roles have read/write visibility
  for their academic review workflows.

## Maintenance notes

- Keep the inverse field name and relation model aligned with
  `models/slide_channel.py`.
- If changing the course action or its defaults, update the section stat button and
  verify the relevant subject and teacher fields remain compatible.
- Add any new XML files to `__manifest__.py` in dependency order.
