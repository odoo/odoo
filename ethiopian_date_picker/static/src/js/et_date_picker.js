// @odoo-module
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import {
  Component,
  useState,
  onWillStart,
  onMounted,
  useEffect,
  useRef,
} from "@odoo/owl";
import { EthiopianDate } from "./ethiopian_date";

class DateTimeEthiopiaField extends Component {
  static template = "ethiopian_date_picker.DateTimeEthiopiaField";
  static props = { ...standardFieldProps };

  setup() {
    this.ETHIOPIAN_MONTHS = [
      "መስከረም",
      "ጥቅምት",
      "ህዳር",
      "ታህሳስ",
      "ጥር",
      "የካቲት",
      "መጋቢት",
      "ሚያዝያ",
      "ግንቦት",
      "ሰኔ",
      "ሐምሌ",
      "ነሐሴ",
      "ጳጉሜ",
    ];
    this.ETHIOPIAN_DAYS = ["እሁድ", "ሰኞ", "ማክሰኞ", "እሮብ", "ሐሙስ", "አርብ", "ቅዳሜ"];
    this.state = useState({
      inputValue: "",
      showCalendar: false,
      currentYear: 0,
      currentMonth: 0,
      currentDay: 0,
      selectedDate: null,
      viewMode: "days",
    });
    this.wrapperRef = useRef("wrapper");

    onWillStart(async () => {
      this.initializeDate();
    });

    onMounted(() => {
      this.formatDate();
      this.setupOutsideClickListener();
    });

    useEffect(
      () => {
        this.syncWithOdooField();
      },
      () => [this.props.value]
    );
  }

  setupOutsideClickListener() {
    const handleOutsideClick = (event) => {
      if (this.wrapperRef.el && !this.wrapperRef.el.contains(event.target)) {
        this.state.showCalendar = false;
      }
    };

    document.addEventListener("click", handleOutsideClick);
  }

  initializeDate = () => {
    const today = new Date();
    const ethiopianDate = EthiopianDate.fromGregorian(today);
    this.state.currentYear = ethiopianDate.year;
    this.state.currentMonth = ethiopianDate.month - 1;
    this.state.currentDay = ethiopianDate.day;
    this.state.inputValue = ethiopianDate.format();


  };

  formatDate = () => {
    if (this.props.value) {
      const date = new Date(this.props.value);
      if (!isNaN(date.getTime())) {
        const ethiopianDate = EthiopianDate.fromGregorian(date);
        this.state.inputValue = ethiopianDate.format();
        this.state.selectedDate = ethiopianDate;
      } 
    } 
  };

  onInputChange = (event) => {
    const inputValue = event.target.value;
    this.state.inputValue = inputValue;

    // Parse the input to see if it's a valid Ethiopian date
    const parsedDate = this.parseEthiopianDate(inputValue);
    if (parsedDate) {
      const selectedDate = new EthiopianDate(
        parsedDate.year,
        parsedDate.month,
        parsedDate.day
      );
      const formattedEthiopianDate = selectedDate.format();

      this.state.currentDay = parsedDate.day;
      this.state.currentMonth = parsedDate.month - 1;
      this.state.currentYear = parsedDate.year;
      this.state.selectedDate = selectedDate;

      // Update input value with formatted Ethiopian date
      this.state.inputValue = formattedEthiopianDate;

      // Update props with the formatted Ethiopian date
      this.props.update(formattedEthiopianDate);

      // Trigger the onchange event with the formatted date if provided
      if (this.props.onchange) {
        this.props.onchange(formattedEthiopianDate);
      }
    }
  };

  parseEthiopianDate = (input) => {
    // Define the Ethiopian date format (DD/MM/YYYY)
    const datePattern = /^(\d{2})\/(\d{2})\/(\d{4})$/;
    const match = input.match(datePattern);
    if (match) {
      const day = parseInt(match[1], 10);
      const month = parseInt(match[2], 10);
      const year = parseInt(match[3], 10);

      // Validate Ethiopian date ranges (Ethiopian calendar uses 1-13 for months, with the 13th month having 5 or 6 days)
      if (this.isValidEthiopianDate(day, month, year)) {
        return { day, month, year };
      }
    }
    return null; // Invalid date
  };

  isValidEthiopianDate = (day, month, year) => {
    // Ethiopian months are 1-13, with the 13th month having 5 or 6 days (depending on leap year)
    const maxDaysInMonth =
      month === 13 ? (this.isEthiopianLeapYear(year) ? 6 : 5) : 30;
    return (
      year >= 1 &&
      month >= 1 &&
      month <= 13 &&
      day >= 1 &&
      day <= maxDaysInMonth
    );
  };

  isEthiopianLeapYear = (year) => {
    // Leap year calculation for the Ethiopian calendar (every 4 years, except for centuries not divisible by 400)
    return year % 4 === 3; // Ethiopian leap years are one year behind Gregorian leap years
  };

  onInputClick = () => {
    this.state.showCalendar = !this.state.showCalendar;
    this.state.viewMode = "days";
  };

  onCalendarHeaderClick = () => {
    if (this.state.viewMode === "days") {
      this.state.viewMode = "months";
    } else if (this.state.viewMode === "months") {
      this.state.viewMode = "years";
    }
  };

  onMonthSelect = (month) => {
    this.state.currentMonth = this.ETHIOPIAN_MONTHS.indexOf(month);
    this.state.viewMode = "days";
  };

  onYearSelect = (year) => {
    this.state.currentYear = year;
    this.state.viewMode = "months";
  };

  getAvailableYears = () => {
    const years = [];
    for (
      let i = this.state.currentYear - 10;
      i <= this.state.currentYear + 10;
      i++
    ) {
      years.push(i);
    }
    return years;
  };

  changeMonth = (delta) => {
    let newMonth = this.state.currentMonth + delta;
    let newYear = this.state.currentYear;

    if (newMonth > 12) {
      newMonth = 0;
      newYear++;
    } else if (newMonth < 0) {
      newMonth = 12;
      newYear--;
    }

    this.state.currentMonth = newMonth;
    this.state.currentYear = newYear;
    this.state.showCalendar = true;
  };

  syncWithOdooField() {
    const odooFieldValue = this.props.value;
    console.log("odooFieldValue", odooFieldValue);
    if (
      odooFieldValue &&
      (!this.state.selectedDate ||
        this.state.selectedDate.toGregorian().toISOString() !== odooFieldValue)
    ) {
      const [day, month, year] = odooFieldValue.split("/");
      const gregorianDate = new EthiopianDate(year, month, day).toGregorian();
      if (!isNaN(gregorianDate.getTime())) {
        try {
          const ethiopianDate = EthiopianDate.fromGregorian(gregorianDate);
          if (
            ethiopianDate &&
            ethiopianDate.year &&
            ethiopianDate.month &&
            ethiopianDate.day
          ) {
            this.state.inputValue = ethiopianDate.format();
            this.state.selectedDate = ethiopianDate;
            this.state.currentYear = ethiopianDate.year;
            this.state.currentMonth = ethiopianDate.month - 1;
          } else {
            console.error("Invalid Ethiopian date");
          }
        } catch (error) {
          console.error("Error converting to Ethiopian date:", error);
        }
      } else {
        console.error("Invalid Gregorian date:", odooFieldValue);
      }
    }
  }

  onDateSelect = (day) => {
    const selectedDate = new EthiopianDate(
      this.state.currentYear,
      this.state.currentMonth + 1,
      day
    );
    const formattedEthiopianDate = selectedDate.format();

    this.state.inputValue = formattedEthiopianDate;
    this.state.selectedDate = selectedDate;
    this.state.showCalendar = false;

    this.props.update(formattedEthiopianDate);

    if (this.props.onchange) {
      this.props.onchange(formattedEthiopianDate);
    }
  };

  getDaysInMonth = (year, month) => {
    if (month < 12) {
      return Array.from({ length: 30 }, (_, i) => i + 1);
    } else {
      return Array.from({ length: year % 4 === 3 ? 6 : 5 }, (_, i) => i + 1);
    }
  };

  isToday = (day) => {
    const today = new Date();
    const ethiopianToday = EthiopianDate.fromGregorian(today);
    return (
      ethiopianToday.year === this.state.currentYear &&
      ethiopianToday.month === this.state.currentMonth + 1 &&
      ethiopianToday.day === day
    );
  };

  getDayOfWeek = (year, month, day) => {
    const ethiopianDate = new EthiopianDate(year, month + 1, day);
    const gregorianDate = ethiopianDate.toGregorian();
    return gregorianDate.getDay();
  };
}

registry.category("fields").add("date_et", DateTimeEthiopiaField);
