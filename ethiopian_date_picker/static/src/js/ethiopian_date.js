/** @odoo-module **/
const Exception = function (message) {
  this.message = message;
  this.name = 'Exception';
};

const startDayOfEthiopian = function (year) {
  const newYearDay = Math.floor(year / 100) - Math.floor(year / 400) - 4;
  // if the prev ethiopian year is a leap year, new-year occurs on 12th
  return ((year - 1) % 4 === 3) ? newYearDay + 1 : newYearDay;
};

const toGregorian = function (dateArray) {
  // Allow argument to be array year, month, day, or 3 separate params
  const inputs = (dateArray.constructor === Array) ? dateArray : [].slice.call(arguments);

  // prevent incorrect input
  if (inputs.indexOf(0) !== -1 || inputs.indexOf(null) !== -1 ||
      inputs.indexOf(undefined) !== -1 || inputs.length !== 3) {
    throw new Exception("Malformed input can't be converted.");
  }

  const [year, month, date] = inputs;
  // Ethiopian new year in Gregorian calendar
  const newYearDay = startDayOfEthiopian(year);

  // September (Ethiopian) sees 7y difference
  let gregorianYear = year + 7;

  // Number of days in gregorian months
  // starting with September (index 1)
  // Index 0 is reserved for leap years switches.
  // Index 4 is December, the final month of the year.
  let gregorianMonths = [0.0, 30, 31, 30, 31, 31, 28, 31, 30, 31, 30, 31, 31, 30];

  // if next gregorian year is leap year, February has 29 days.
  const nextYear = gregorianYear + 1;
  if ((nextYear % 4 === 0 && nextYear % 100 !== 0) || nextYear % 400 === 0) {
    gregorianMonths[6] = 29;
  }

  // calculate number of days up to that date
  let until = ((month - 1) * 30.0) + date;
  if (until <= 37 && year <= 1575) { // mysterious rule
    until += 28;
    gregorianMonths[0] = 31;
  } else {
    until += newYearDay - 1;
  }

  // if ethiopian year is leap year, pagumen has six days
  if (year - 1 % 4 === 3) {
    until += 1;
  }

  // calculate month and date increment
  let m = 0;
  let gregorianDate;
  for (let i = 0; i < gregorianMonths.length; i++) {
    if (until <= gregorianMonths[i]) {
      m = i;
      gregorianDate = until;
      break;
    } else {
      m = i;
      until -= gregorianMonths[i];
    }
  }

  // if m > 4, we're already on next Gregorian year
  if (m > 4) {
    gregorianYear += 1;
  }

  // Gregorian months ordered according to Ethiopian
  const order = [8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9];
  gregorianMonths = order[m];
  return [gregorianYear, gregorianMonths, gregorianDate];
};

const toEthiopian = function (dateArray) {
  // Allow argument to be array year, month, day, or 3 separate params
  const inputs = (dateArray.constructor === Array) ? dateArray : [].slice.call(arguments);

  // prevent incorect input
  if (inputs.indexOf(0) !== -1 || inputs.indexOf(null) !== -1 ||
      inputs.indexOf(undefined) !== -1 || inputs.length !== 3) {
    throw new Exception("Malformed input can't be converted.");
  }

  const [year, month, date] = inputs;

  // date between 5 and 14 of May 1582 are invalid
  if (month === 10 && date >= 5 && date <= 14 && year === 1582) {
    throw new Exception('Invalid Date between 5-14 May 1582.');
  }

  // Number of days in gregorian months
  // starting with January (index 1)
  // Index 0 is reserved for leap years switches.
  const gregorianMonths = [0.0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

  // Number of days in ethiopian months
  // starting with January (index 1)
  // Index 0 is reserved for leap years switches.
  // Index 10 is month 13, the final month of the year
  const ethiopianMonths = [0.0, 30, 30, 30, 30, 30, 30, 30, 30, 30, 5, 30, 30, 30, 30];

  // if gregorian leap year, February has 29 days.
  if ((year % 4 === 0 && year % 100 !== 0) || year % 400 === 0) {
    gregorianMonths[2] = 29;
  }

  // September sees 8y difference
  let ethiopianYear = year - 8;

  // if ethiopian leap year pagumain has 6 days
  if (ethiopianYear % 4 === 3) {
    ethiopianMonths[10] = 6;
  }

  // Ethiopian new year in Gregorian calendar
  const newYearDay = startDayOfEthiopian(year - 8);

  // calculate number of days up to that date
  let until = 0;
  for (let i = 1; i < month; i++) {
    until += gregorianMonths[i];
  }
  until += date;

  // update tahissas (december) to match january 1st
  let tahissas = (ethiopianYear % 4) === 0 ? 26 : 25;

  // take into account the 1582 change
  if (year < 1582) {
    ethiopianMonths[1] = 0;
    ethiopianMonths[2] = tahissas;
  } else if (until <= 277 && year === 1582) {
    ethiopianMonths[1] = 0;
    ethiopianMonths[2] = tahissas;
  } else {
    tahissas = newYearDay - 3;
    ethiopianMonths[1] = tahissas;
  }

  // calculate month and date incremently
  let m;
  let ethiopianDate;
  for (m = 1; m < ethiopianMonths.length; m++) {
    if (until <= ethiopianMonths[m]) {
      ethiopianDate = (m === 1 || ethiopianMonths[m] === 0) ? until + (30 - tahissas) : until;
      break;
    } else {
      until -= ethiopianMonths[m];
    }
  }

  // if m > 10, we're already on next Ethiopian year
  if (m > 10) {
    ethiopianYear += 1;
  }

  // Ethiopian months ordered according to Gregorian
  const order = [0, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 1, 2, 3, 4];
  const ethiopianMonth = order[m];
  return [ethiopianYear, ethiopianMonth, ethiopianDate];
};

export class EthiopianDate {
    constructor(year, month, day) {
        if (!year || !month || !day) {
             throw new Error("EthiopianDate constructor requires year, month, and day arguments.");
        }
        this.year = parseInt(year, 10);
        this.month = parseInt(month, 10);
        this.day = parseInt(day, 10);
    }

    static fromGregorian(date) {
        const [year, month, day] = toEthiopian([date.getFullYear(), date.getMonth() + 1, date.getDate()]);
        return new EthiopianDate(year, month, day);
    }

    toGregorian() {
        const [year, month, day] = toGregorian([this.year, this.month, this.day]);
        return new Date(year, month - 1, day);
    }

    format() {
        return `${this.day.toString().padStart(2, '0')}/${this.month.toString().padStart(2, '0')}/${this.year}`;
    }

}









