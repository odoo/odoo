const { DateTime } = luxon;

export function fireCourse(course, { minutesAgo = 0 } = {}) {
    course.fired = true;
    course.fired_date = DateTime.now().minus({ minutes: minutesAgo });
    return course;
}
