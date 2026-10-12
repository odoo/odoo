/*!
FullCalendar (Vanilla JS) v7.1.0
Docs & License: https://fullcalendar.io
(c) 2026 Adam Shaw
*/
(function ({ F: globalLocales }) {
  

  var __zh_tw$l78 = {
      code: 'zh-tw',
      prevText: '上個',
      nextText: '下個',
      todayText: '今天',
      yearText: '年',
      monthText: '月',
      weekTextLong: '週',
      dayText: '天',
      listText: '活動列表',
      allDayText: '整天',
      moreLinkText: '顯示更多',
      noEventsText: '沒有任何活動',
  };

  var __zh_cn$l77 = {
      code: 'zh-cn',
      week: {
          // GB/T 7408-1994《数据元和交换格式·信息交换·日期和时间表示法》与ISO 8601:1988等效
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: '上月',
      nextText: '下月',
      todayText: '今天',
      yearText: '年',
      monthText: '月',
      weekTextLong: '周',
      dayText: '日',
      listText: '日程',
      allDayText: '全天',
      moreLinkText(n) {
          return '另外 ' + n + ' 个';
      },
      noEventsText: '没有事件显示',
  };

  var __vi$l76 = {
      code: 'vi',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Trước',
      nextText: 'Tiếp',
      todayText: 'Hôm nay',
      yearText: 'Năm',
      monthText: 'Tháng',
      weekTextLong: 'Tuần',
      weekTextShort: 'Tu',
      dayText: 'Ngày',
      listText: 'Lịch biểu',
      allDayText: 'Cả ngày',
      moreLinkText(n) {
          return '+ thêm ' + n;
      },
      noEventsText: 'Không có sự kiện để hiển thị',
  };

  var __uz$l75 = {
      code: 'uz',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Oldingi',
      nextText: 'Keyingi',
      todayText: 'Bugun',
      yearText: 'Yil',
      monthText: 'Oy',
      weekTextLong: 'Xafta',
      dayText: 'Kun',
      listText: 'Kun tartibi',
      allDayText: 'Kun bo\'yi',
      moreLinkText(n) {
          return '+ yana ' + n;
      },
      noEventsText: 'Ko\'rsatish uchun voqealar yo\'q',
  };

  var __uz_cy$l74 = {
      code: 'uz-cy',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Олин',
      nextText: 'Кейин',
      todayText: 'Бугун',
      monthText: 'Ой',
      weekTextLong: 'Ҳафта',
      dayText: 'Кун',
      listText: 'Кун тартиби',
      allDayText: 'Кун\nбўйича',
      moreLinkText(n) {
          return '+ яна ' + n;
      },
      noEventsText: 'Кўрсатиш учун воқеалар йўқ',
  };

  var __uk$l73 = {
      code: 'uk',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 7, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'Попередній',
      nextText: 'далі',
      todayText: 'Сьогодні',
      yearText: 'рік',
      monthText: 'Місяць',
      weekTextLong: 'Тиждень',
      weekTextShort: 'Тиж',
      dayText: 'День',
      listText: 'Порядок денний',
      allDayText: 'Увесь\nдень',
      moreLinkText(n) {
          return '+ще ' + n + '...';
      },
      noEventsText: 'Немає подій для відображення',
  };

  var __ug$l72 = {
      code: 'ug',
      prevText: 'ئالدىنقى',
      nextText: 'كېيىنكى',
      todayText: 'بۈگۈن',
      yearText: 'يىل',
      monthText: 'ئاي',
      weekTextLong: 'ھەپتە',
      dayText: 'كۈن',
      listText: 'كۈنتەرتىپ',
      allDayText: 'پۈتۈن كۈن',
  };

  var __tr$l71 = {
      code: 'tr',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 7, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'geri',
      nextText: 'ileri',
      todayText: 'bugün',
      yearText: 'Yıl',
      monthText: 'Ay',
      weekTextLong: 'Hafta',
      weekTextShort: 'Hf',
      dayText: 'Gün',
      listText: 'Ajanda',
      allDayText: 'Tüm gün',
      moreLinkText: 'daha fazla',
      noEventsText: 'Gösterilecek etkinlik yok',
  };

  var __th$l70 = {
      code: 'th',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'ก่อนหน้า',
      nextText: 'ถัดไป',
      prevYearText: 'ปีก่อนหน้า',
      nextYearText: 'ปีถัดไป',
      yearText: 'ปี',
      todayText: 'วันนี้',
      monthText: 'เดือน',
      weekTextLong: 'สัปดาห์',
      dayText: 'วัน',
      listText: 'กำหนดการ',
      allDayText: 'ตลอดวัน',
      moreLinkText: 'เพิ่มเติม',
      noEventsText: 'ไม่มีกิจกรรมที่จะแสดง',
  };

  var __ta_in$l69 = {
      code: 'ta-in',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'முந்தைய',
      nextText: 'அடுத்தது',
      todayText: 'இன்று',
      yearText: 'ஆண்டு',
      monthText: 'மாதம்',
      weekTextLong: 'வாரம்',
      dayText: 'நாள்',
      listText: 'தினசரி அட்டவணை',
      allDayText: 'நாள்\nமுழுவதும்',
      moreLinkText(n) {
          return '+ மேலும் ' + n;
      },
      noEventsText: 'காண்பிக்க நிகழ்வுகள் இல்லை',
  };

  var __sv$l68 = {
      code: 'sv',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Förra',
      nextText: 'Nästa',
      todayText: 'Idag',
      yearText: 'År',
      monthText: 'Månad',
      weekTextLong: 'Vecka',
      weekTextShort: 'v.',
      dayText: 'Dag',
      listText: 'Program',
      prevHint(unitText) {
          return `Föregående ${unitText.toLocaleLowerCase()}`;
      },
      nextHint(unitText) {
          return `Nästa ${unitText.toLocaleLowerCase()}`;
      },
      todayHint(unitText, unit) {
          return (unit === 'year' ? 'I' : 'Denna') + ' ' + unitText.toLocaleLowerCase();
      },
      viewHint: '$0 vy',
      navLinkHint: 'Gå till $0',
      moreLinkHint(eventCnt) {
          return `Visa ytterligare ${eventCnt} händelse${eventCnt === 1 ? '' : 'r'}`;
      },
      allDayText: 'Heldag',
      moreLinkText: 'till',
      noEventsText: 'Inga händelser att visa',
      closeHint: 'Stäng',
      eventsHint: 'Händelser',
  };

  var __sr$l67 = {
      code: 'sr',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 7, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'Prethodna',
      nextText: 'Sledeći',
      todayText: 'Danas',
      yearText: 'Godina',
      monthText: 'Mеsеc',
      weekTextLong: 'Nеdеlja',
      weekTextShort: 'Sed',
      dayText: 'Dan',
      listText: 'Planеr',
      allDayText: 'Cеo dan',
      moreLinkText(n) {
          return '+ još ' + n;
      },
      noEventsText: 'Nеma događaja za prikaz',
  };

  var __sr_cyrl$l66 = {
      code: 'sr-cyrl',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 7, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'Претходна',
      nextText: 'следећи',
      todayText: 'Данас',
      yearText: 'Година',
      monthText: 'Месец',
      weekTextLong: 'Недеља',
      weekTextShort: 'Сед',
      dayText: 'Дан',
      listText: 'Планер',
      allDayText: 'Цео дан',
      moreLinkText(n) {
          return '+ још ' + n;
      },
      noEventsText: 'Нема догађаја за приказ',
  };

  var __sq$l65 = {
      code: 'sq',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'mbrapa',
      nextText: 'Përpara',
      todayText: 'Sot',
      yearText: 'Viti',
      monthText: 'Muaj',
      weekTextLong: 'Javë',
      weekTextShort: 'Ja',
      dayText: 'Ditë',
      listText: 'Listë',
      allDayText: 'Gjithë\nditën',
      moreLinkText(n) {
          return '+më tepër ' + n;
      },
      noEventsText: 'Nuk ka evente për të shfaqur',
  };

  var __sm$l64 = {
      code: 'sm',
      prevText: 'Talu ai',
      nextText: 'Mulimuli atu',
      todayText: 'Aso nei',
      yearText: 'Tausaga',
      monthText: 'Masina',
      weekTextLong: 'Vaiaso',
      dayText: 'Aso',
      listText: 'Faasologa',
      allDayText: 'Aso atoa',
      moreLinkText: 'sili atu',
      noEventsText: 'Leai ni mea na tutupu',
  };

  var __sl$l63 = {
      code: 'sl',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 7, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'Prejšnji',
      nextText: 'Naslednji',
      todayText: 'Trenutni',
      yearText: 'Leto',
      monthText: 'Mesec',
      weekTextLong: 'Teden',
      dayText: 'Dan',
      listText: 'Dnevni red',
      allDayText: 'Ves dan',
      moreLinkText: 'več',
      noEventsText: 'Ni dogodkov za prikaz',
  };

  var __sk$l62 = {
      code: 'sk',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Predchádzajúci',
      nextText: 'Nasledujúci',
      todayText: 'Dnes',
      yearText: 'Rok',
      monthText: 'Mesiac',
      weekTextLong: 'Týždeň',
      weekTextShort: 'Ty',
      dayText: 'Deň',
      listText: 'Rozvrh',
      allDayText: 'Celý deň',
      moreLinkText(n) {
          return '+ďalšie: ' + n;
      },
      noEventsText: 'Žiadne akcie na zobrazenie',
  };

  var __si_lk$l61 = {
      code: 'si-lk',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'පෙර',
      nextText: 'පසු',
      todayText: 'අද',
      yearText: 'අවුරුදු',
      monthText: 'මාසය',
      weekTextLong: 'සතිය',
      weekTextShort: 'සති',
      dayText: 'දවස',
      listText: 'ලැයිස්තුව',
      allDayText: 'සියලු',
      moreLinkText: 'තවත්',
      noEventsText: 'මුකුත් නැත',
  };

  var __ru$l60 = {
      code: 'ru',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Пред',
      nextText: 'След',
      todayText: 'Сегодня',
      yearText: 'Год',
      monthText: 'Месяц',
      weekTextLong: 'Неделя',
      weekTextShort: 'Нед',
      dayText: 'День',
      listText: 'Повестка дня',
      allDayText: 'Весь\nдень',
      moreLinkText(n) {
          return '+ ещё ' + n;
      },
      noEventsText: 'Нет событий для отображения',
  };

  var __ro$l59 = {
      code: 'ro',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 7, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'precedentă',
      nextText: 'următoare',
      todayText: 'Azi',
      yearText: 'An',
      monthText: 'Lună',
      weekTextLong: 'Săptămână',
      weekTextShort: 'Săpt',
      dayText: 'Zi',
      listText: 'Agendă',
      allDayText: 'Toată\nziua',
      moreLinkText(n) {
          return '+alte ' + n;
      },
      noEventsText: 'Nu există evenimente de afișat',
  };

  var __pt$l58 = {
      code: 'pt',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Anterior',
      nextText: 'Seguinte',
      todayText: 'Hoje',
      yearText: 'Ano',
      monthText: 'Mês',
      weekTextLong: 'Semana',
      weekTextShort: 'Sem',
      dayText: 'Dia',
      listText: 'Agenda',
      allDayText: 'Todo\no dia',
      moreLinkText: 'mais',
      noEventsText: 'Não há eventos para mostrar',
  };

  var __pt_br$l57 = {
      code: 'pt-br',
      prevText: 'Anterior',
      nextText: 'Próximo',
      prevYearText: 'Ano anterior',
      nextYearText: 'Próximo ano',
      yearText: 'Ano',
      todayText: 'Hoje',
      monthText: 'Mês',
      weekTextLong: 'Semana',
      weekTextShort: 'Sm',
      dayText: 'Dia',
      listText: 'Lista',
      prevHint: '$0 Anterior',
      nextHint: 'Próximo $0',
      todayHint(unitText, unit) {
          return (unit === 'day') ? 'Hoje' :
              ((unit === 'week') ? 'Esta' : 'Este') + ' ' + unitText.toLocaleLowerCase();
      },
      viewHint(unitText, unit) {
          return 'Visualizar ' + (unit === 'week' ? 'a' : 'o') + ' ' + unitText.toLocaleLowerCase();
      },
      allDayText: 'Dia\ninteiro',
      moreLinkText(n) {
          return 'mais +' + n;
      },
      moreLinkHint(eventCnt) {
          return `Mostrar mais ${eventCnt} eventos`;
      },
      noEventsText: 'Não há eventos para mostrar',
      navLinkHint: 'Ir para $0',
      closeHint: 'Fechar',
      eventsHint: 'Eventos',
  };

  var __pl$l56 = {
      code: 'pl',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Poprzedni',
      nextText: 'Następny',
      todayText: 'Dziś',
      yearText: 'Rok',
      monthText: 'Miesiąc',
      weekTextLong: 'Tydzień',
      weekTextShort: 'Tydz',
      dayText: 'Dzień',
      listText: 'Plan dnia',
      allDayText: 'Cały\ndzień',
      moreLinkText: 'więcej',
      noEventsText: 'Brak wydarzeń do wyświetlenia',
  };

  var __nn$l55 = {
      code: 'nn',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Førre',
      nextText: 'Neste',
      todayText: 'I dag',
      yearText: 'År',
      monthText: 'Månad',
      weekTextLong: 'Veke',
      dayText: 'Dag',
      listText: 'Agenda',
      allDayText: 'Heile\ndagen',
      moreLinkText: 'til',
      noEventsText: 'Ingen hendelser å vise',
  };

  var __nl$l54 = {
      code: 'nl',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Vorige',
      nextText: 'Volgende',
      todayText: 'Vandaag',
      yearText: 'Jaar',
      monthText: 'Maand',
      weekTextLong: 'Week',
      dayText: 'Dag',
      listText: 'Lijst',
      allDayText: 'Hele dag',
      moreLinkText: 'extra',
      noEventsText: 'Geen evenementen om te laten zien',
  };

  var __ne$l53 = {
      code: 'ne', // code for nepal
      week: {
          dow: 7, // Sunday is the first day of the week.
          doy: 1, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'अघिल्लो',
      nextText: 'अर्को',
      todayText: 'आज',
      yearText: 'वर्ष',
      monthText: 'महिना',
      weekTextLong: 'हप्ता',
      dayText: 'दिन',
      listText: 'सूची',
      allDayText: 'दिनभरि',
      moreLinkText: 'थप लिंक',
      noEventsText: 'देखाउनको लागि कुनै घटनाहरू छैनन्',
  };

  var __nb$l52 = {
      code: 'nb',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Forrige',
      nextText: 'Neste',
      todayText: 'I dag',
      yearText: 'År',
      monthText: 'Måned',
      weekTextLong: 'Uke',
      dayText: 'Dag',
      listText: 'Agenda',
      allDayText: 'Hele\ndagen',
      moreLinkText: 'til',
      noEventsText: 'Ingen hendelser å vise',
      prevHint: 'Forrige $0',
      nextHint: 'Neste $0',
      todayHint: 'Nåværende $0',
      viewHint: '$0 visning',
      navLinkHint: 'Gå til $0',
      moreLinkHint(eventCnt) {
          return `Vis ${eventCnt} flere hendelse${eventCnt === 1 ? '' : 'r'}`;
      },
  };

  var __ms$l51 = {
      code: 'ms',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 7, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'Sebelum',
      nextText: 'Selepas',
      todayText: 'hari ini',
      yearText: 'Tahun',
      monthText: 'Bulan',
      weekTextLong: 'Minggu',
      weekTextShort: 'Mg',
      dayText: 'Hari',
      listText: 'Agenda',
      allDayText: 'Sepanjang\nhari',
      moreLinkText(n) {
          return 'masih ada ' + n + ' acara';
      },
      noEventsText: 'Tiada peristiwa untuk dipaparkan',
  };

  var __mk$l50 = {
      code: 'mk',
      prevText: 'претходно',
      nextText: 'следно',
      todayText: 'Денес',
      yearText: 'година',
      monthText: 'Месец',
      weekTextLong: 'Недела',
      weekTextShort: 'Сед',
      dayText: 'Ден',
      listText: 'График',
      allDayText: 'Цел ден',
      moreLinkText(n) {
          return '+повеќе ' + n;
      },
      noEventsText: 'Нема настани за прикажување',
  };

  var __lv$l49 = {
      code: 'lv',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Iepr.',
      nextText: 'Nāk.',
      todayText: 'Šodien',
      yearText: 'Gads',
      monthText: 'Mēnesis',
      weekTextLong: 'Nedēļa',
      weekTextShort: 'Ned.',
      dayText: 'Diena',
      listText: 'Dienas kārtība',
      allDayText: 'Visu\ndienu',
      moreLinkText(n) {
          return '+vēl ' + n;
      },
      noEventsText: 'Nav notikumu',
  };

  var __lt$l48 = {
      code: 'lt',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Atgal',
      nextText: 'Pirmyn',
      todayText: 'Šiandien',
      yearText: 'Metai',
      monthText: 'Mėnuo',
      weekTextLong: 'Savaitė',
      weekTextShort: 'SAV',
      dayText: 'Diena',
      listText: 'Darbotvarkė',
      allDayText: 'Visą\ndieną',
      moreLinkText: 'daugiau',
      noEventsText: 'Nėra įvykių rodyti',
  };

  var __lb$l47 = {
      code: 'lb',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Zréck',
      nextText: 'Weider',
      todayText: 'Haut',
      yearText: 'Joer',
      monthText: 'Mount',
      weekTextLong: 'Woch',
      weekTextShort: 'W',
      dayText: 'Dag',
      listText: 'Terminiwwersiicht',
      allDayText: 'Ganzen\nDag',
      moreLinkText: 'méi',
      noEventsText: 'Nee Evenementer ze affichéieren',
  };

  var __ku$l46 = {
      code: 'ku',
      week: {
          dow: 6, // Saturday is the first day of the week.
          doy: 12, // The week that contains Jan 1st is the first week of the year.
      },
      direction: 'rtl',
      prevText: 'پێشتر',
      nextText: 'دواتر',
      todayText: 'ئەمڕو',
      yearText: 'ساڵ',
      monthText: 'مانگ',
      weekTextLong: 'هەفتە',
      dayText: 'ڕۆژ',
      listText: 'بەرنامە',
      allDayText: 'هەموو ڕۆژەکە',
      moreLinkText: 'زیاتر',
      noEventsText: 'هیچ ڕووداوێك نیە',
  };

  var __ko$l45 = {
      code: 'ko',
      prevText: '이전달',
      nextText: '다음달',
      todayText: '오늘',
      yearText: '년도',
      monthText: '월',
      weekTextLong: '주',
      dayText: '일',
      listText: '일정목록',
      allDayText: '종일',
      moreLinkText: '개',
      noEventsText: '일정이 없습니다',
  };

  var __km$l44 = {
      code: 'km',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'មុន',
      nextText: 'បន្ទាប់',
      todayText: 'ថ្ងៃនេះ',
      yearText: 'ឆ្នាំ',
      monthText: 'ខែ',
      weekTextLong: 'សប្តាហ៍',
      dayText: 'ថ្ងៃ',
      listText: 'បញ្ជី',
      allDayText: 'ពេញមួយថ្ងៃ',
      moreLinkText: 'ច្រើនទៀត',
      noEventsText: 'គ្មានព្រឹត្តិការណ៍ត្រូវបង្ហាញ',
  };

  var __kk$l43 = {
      code: 'kk',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 7, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'Алдыңғы',
      nextText: 'Келесі',
      todayText: 'Бүгін',
      yearText: 'Жыл',
      monthText: 'Ай',
      weekTextLong: 'Апта',
      dayText: 'Күн',
      listText: 'Күн тәртібі',
      allDayText: 'Күні\nбойы',
      moreLinkText(n) {
          return '+ тағы ' + n;
      },
      noEventsText: 'Көрсету үшін оқиғалар жоқ',
  };

  var __ka$l42 = {
      code: 'ka',
      week: {
          dow: 1,
          doy: 7,
      },
      prevText: 'წინა',
      nextText: 'შემდეგი',
      todayText: 'დღეს',
      yearText: 'წელიწადი',
      monthText: 'თვე',
      weekTextLong: 'კვირა',
      weekTextShort: 'კვ',
      dayText: 'დღე',
      listText: 'დღის წესრიგი',
      allDayText: 'მთელი\nდღე',
      moreLinkText(n) {
          return '+ კიდევ ' + n;
      },
      noEventsText: 'ღონისძიებები არ არის',
  };

  var __ja$l41 = {
      code: 'ja',
      prevText: '前',
      nextText: '次',
      todayText: '今日',
      yearText: '年',
      monthText: '月',
      weekTextLong: '週',
      dayText: '日',
      listText: '予定リスト',
      allDayText: '終日',
      moreLinkText(n) {
          return '他 ' + n + ' 件';
      },
      noEventsText: '表示する予定はありません',
  };

  var __it$l40 = {
      code: 'it',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Prec',
      nextText: 'Succ',
      todayText: 'Oggi',
      yearText: 'Anno',
      monthText: 'Mese',
      weekTextLong: 'Settimana',
      weekTextShort: 'Sm',
      dayText: 'Giorno',
      listText: 'Agenda',
      allDayText: 'Tutto\nil giorno',
      moreLinkText(n) {
          return '+altri ' + n;
      },
      noEventsText: 'Non ci sono eventi da visualizzare',
  };

  var __is$l39 = {
      code: 'is',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Fyrri',
      nextText: 'Næsti',
      todayText: 'Í dag',
      yearText: 'Ár',
      monthText: 'Mánuður',
      weekTextLong: 'Vika',
      dayText: 'Dagur',
      listText: 'Dagskrá',
      allDayText: 'Allan\ndaginn',
      moreLinkText: 'meira',
      noEventsText: 'Engir viðburðir til að sýna',
  };

  var __id$l38 = {
      code: 'id',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 7, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'mundur',
      nextText: 'maju',
      todayText: 'hari ini',
      yearText: 'Tahun',
      monthText: 'Bulan',
      weekTextLong: 'Minggu',
      weekTextShort: 'Mg',
      dayText: 'Hari',
      listText: 'Agenda',
      allDayText: 'Sehari\npenuh',
      moreLinkText: 'lebih',
      noEventsText: 'Tidak ada acara untuk ditampilkan',
  };

  var __hy_am$l37 = {
      code: 'hy-am',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Նախորդ',
      nextText: 'Հաջորդ',
      todayText: 'Այսօր',
      yearText: 'Տարի',
      monthText: 'Ամիս',
      weekTextLong: 'Շաբաթ',
      weekTextShort: 'Շաբ',
      dayText: 'Օր',
      listText: 'Օրվա ցուցակ',
      allDayText: 'Ամբողջ օր',
      moreLinkText(n) {
          return '+ ևս ' + n;
      },
      noEventsText: 'Բացակայում է իրադարձությունը ցուցադրելու',
  };

  var __hu$l36 = {
      code: 'hu',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Vissza',
      nextText: 'Előre',
      todayText: 'Ma',
      yearText: 'Év',
      monthText: 'Hónap',
      weekTextLong: 'Hét',
      dayText: 'Nap',
      listText: 'Lista',
      allDayText: 'Egész\nnap',
      moreLinkText: 'további',
      noEventsText: 'Nincs megjeleníthető esemény',
  };

  var __hr$l35 = {
      code: 'hr',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 7, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'Prijašnji',
      nextText: 'Sljedeći',
      todayText: 'Danas',
      yearText: 'Godina',
      monthText: 'Mjesec',
      weekTextLong: 'Tjedan',
      weekTextShort: 'Tje',
      dayText: 'Dan',
      listText: 'Raspored',
      allDayText: 'Cijeli\ndan',
      moreLinkText(n) {
          return '+ još ' + n;
      },
      noEventsText: 'Nema događaja za prikaz',
  };

  var __hi$l34 = {
      code: 'hi',
      week: {
          dow: 0, // Sunday is the first day of the week.
          doy: 6, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'पिछला',
      nextText: 'अगला',
      todayText: 'आज',
      yearText: 'वर्ष',
      monthText: 'महीना',
      weekTextLong: 'सप्ताह',
      weekTextShort: 'हफ्ता',
      dayText: 'दिन',
      listText: 'कार्यसूची',
      allDayText: 'सभी दिन',
      moreLinkText(n) {
          return '+अधिक ' + n;
      },
      noEventsText: 'कोई घटनाओं को प्रदर्शित करने के लिए',
  };

  var __he$l33 = {
      code: 'he',
      direction: 'rtl',
      prevText: 'הקודם',
      nextText: 'הבא',
      todayText: 'היום',
      yearText: 'שנה',
      monthText: 'חודש',
      weekTextLong: 'שבוע',
      dayText: 'יום',
      listText: 'סדר יום',
      allDayText: 'כל היום',
      moreLinkText: 'נוספים',
      noEventsText: 'אין אירועים להצגה',
  };

  var __gl$l32 = {
      code: 'gl',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Ant',
      nextText: 'Seg',
      todayText: 'Hoxe',
      yearText: 'Ano',
      monthText: 'Mes',
      weekTextLong: 'Semana',
      weekTextShort: 'Sm',
      dayText: 'Día',
      listText: 'Axenda',
      prevHint: '$0 antes',
      nextHint: '$0 seguinte',
      todayHint(unitText, unit) {
          return (unit === 'day') ? 'Hoxe' :
              ((unit === 'week') ? 'Esta' : 'Este') + ' ' + unitText.toLocaleLowerCase();
      },
      viewHint(unitText, unit) {
          return 'Vista ' + (unit === 'week' ? 'da' : 'do') + ' ' + unitText.toLocaleLowerCase();
      },
      allDayText: 'Todo\no día',
      moreLinkText: 'máis',
      moreLinkHint(eventCnt) {
          return `Amosar ${eventCnt} eventos máis`;
      },
      noEventsText: 'Non hai eventos para amosar',
      navLinkHint: 'Ir ao $0',
      closeHint: 'Pechar',
      eventsHint: 'Eventos',
  };

  var __fr$l31 = {
      code: 'fr',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Précédent',
      nextText: 'Suivant',
      todayText: 'Aujourd\'hui',
      yearText: 'Année',
      monthText: 'Mois',
      weekTextLong: 'Semaine',
      weekTextShort: 'Sem.',
      dayText: 'Jour',
      listText: 'Planning',
      allDayText: 'Toute la\njournée',
      moreLinkText: 'en plus',
      noEventsText: 'Aucun évènement à afficher',
  };

  var __fr_ch$l30 = {
      code: 'fr-ch',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Précédent',
      nextText: 'Suivant',
      todayText: 'Courant',
      yearText: 'Année',
      monthText: 'Mois',
      weekTextLong: 'Semaine',
      weekTextShort: 'Sm',
      dayText: 'Jour',
      listText: 'Mon planning',
      allDayText: 'Toute la\njournée',
      moreLinkText: 'en plus',
      noEventsText: 'Aucun évènement à afficher',
  };

  var __fr_ca$l29 = {
      code: 'fr',
      prevText: 'Précédent',
      nextText: 'Suivant',
      todayText: 'Aujourd\'hui',
      yearText: 'Année',
      monthText: 'Mois',
      weekTextLong: 'Semaine',
      weekTextShort: 'Sem.',
      dayText: 'Jour',
      listText: 'Mon planning',
      allDayText: 'Toute la\njournée',
      moreLinkText: 'en plus',
      noEventsText: 'Aucun évènement à afficher',
  };

  var __fi$l28 = {
      code: 'fi',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Edellinen',
      nextText: 'Seuraava',
      todayText: 'Tänään',
      yearText: 'Vuosi',
      monthText: 'Kuukausi',
      weekTextLong: 'Viikko',
      weekTextShort: 'Vk',
      dayText: 'Päivä',
      listText: 'Tapahtumat',
      allDayText: 'Koko\npäivä',
      moreLinkText: 'lisää',
      noEventsText: 'Ei näytettäviä tapahtumia',
  };

  var __fa$l27 = {
      code: 'fa',
      week: {
          dow: 6, // Saturday is the first day of the week.
          doy: 12, // The week that contains Jan 1st is the first week of the year.
      },
      direction: 'rtl',
      prevText: 'قبلی',
      nextText: 'بعدی',
      todayText: 'امروز',
      yearText: 'سال',
      monthText: 'ماه',
      weekTextLong: 'هفته',
      weekTextShort: 'هف',
      dayText: 'روز',
      listText: 'برنامه',
      allDayText: 'تمام روز',
      moreLinkText(n) {
          return 'بیش از ' + n;
      },
      noEventsText: 'هیچ رویدادی به نمایش',
  };

  var __eu$l26 = {
      code: 'eu',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 7, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'Aur',
      nextText: 'Hur',
      todayText: 'Gaur',
      yearText: 'Urtea',
      monthText: 'Hilabetea',
      weekTextLong: 'Astea',
      weekTextShort: 'As',
      dayText: 'Eguna',
      listText: 'Agenda',
      allDayText: 'Egun\nosoa',
      moreLinkText: 'gehiago',
      noEventsText: 'Ez dago ekitaldirik erakusteko',
  };

  var __et$l25 = {
      code: 'et',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Eelnev',
      nextText: 'Järgnev',
      todayText: 'Täna',
      yearText: 'Aasta',
      monthText: 'Kuu',
      weekTextLong: 'Nädal',
      weekTextShort: 'Näd',
      dayText: 'Päev',
      listText: 'Päevakord',
      allDayText: 'Kogu\npäev',
      moreLinkText(n) {
          return '+ veel ' + n;
      },
      noEventsText: 'Kuvamiseks puuduvad sündmused',
  };

  var __es$l24 = {
      code: 'es',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Ant',
      nextText: 'Sig',
      todayText: 'Hoy',
      yearText: 'Año',
      monthText: 'Mes',
      weekTextLong: 'Semana',
      weekTextShort: 'Sm',
      dayText: 'Día',
      listText: 'Agenda',
      prevHint: '$0 antes',
      nextHint: '$0 siguiente',
      todayHint(unitText, unit) {
          return (unit === 'day') ? 'Hoy' :
              ((unit === 'week') ? 'Esta' : 'Este') + ' ' + unitText.toLocaleLowerCase();
      },
      viewHint(unitText, unit) {
          return 'Vista ' + (unit === 'week' ? 'de la' : 'del') + ' ' + unitText.toLocaleLowerCase();
      },
      allDayText: 'Todo\nel día',
      moreLinkText: 'más',
      moreLinkHint(eventCnt) {
          return `Mostrar ${eventCnt} eventos más`;
      },
      noEventsText: 'No hay eventos para mostrar',
      navLinkHint: 'Ir al $0',
      closeHint: 'Cerrar',
      eventsHint: 'Eventos',
  };

  var __es_us$l23 = {
      code: 'es',
      week: {
          dow: 0, // Sunday is the first day of the week.
          doy: 6, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'Ant',
      nextText: 'Sig',
      todayText: 'Hoy',
      yearText: 'Año',
      monthText: 'Mes',
      weekTextLong: 'Semana',
      weekTextShort: 'Sm',
      dayText: 'Día',
      listText: 'Agenda',
      prevHint: '$0 antes',
      nextHint: '$0 siguiente',
      todayHint(unitText, unit) {
          return (unit === 'day') ? 'Hoy' :
              ((unit === 'week') ? 'Esta' : 'Este') + ' ' + unitText.toLocaleLowerCase();
      },
      viewHint(unitText, unit) {
          return 'Vista ' + (unit === 'week' ? 'de la' : 'del') + ' ' + unitText.toLocaleLowerCase();
      },
      allDayText: 'Todo\nel día',
      moreLinkText: 'más',
      noEventsText: 'No hay eventos para mostrar',
  };

  var __eo$l22 = {
      code: 'eo',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Antaŭa',
      nextText: 'Sekva',
      todayText: 'Hodiaŭ',
      yearText: 'Jaro',
      monthText: 'Monato',
      weekTextLong: 'Semajno',
      weekTextShort: 'Sm',
      dayText: 'Tago',
      listText: 'Tagordo',
      allDayText: 'Tuta\ntago',
      moreLinkText: 'pli',
      noEventsText: 'Neniuj eventoj por montri',
  };

  var __en_nz$l21 = {
      code: 'en-nz',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      weekTextShort: 'W',
      todayHint: 'This $0',
      prevHint: 'Previous $0',
      nextHint: 'Next $0',
      viewHint: '$0 view',
      navLinkHint: 'Go to $0',
      moreLinkHint(eventCnt) {
          return `Show ${eventCnt} more event${eventCnt === 1 ? '' : 's'}`;
      },
  };

  var __en_gb$l20 = {
      code: 'en-gb',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      weekTextShort: 'W',
      todayHint: 'This $0',
      prevHint: 'Previous $0',
      nextHint: 'Next $0',
      viewHint: '$0 view',
      navLinkHint: 'Go to $0',
      moreLinkHint(eventCnt) {
          return `Show ${eventCnt} more event${eventCnt === 1 ? '' : 's'}`;
      },
  };

  var __en_au$l19 = {
      code: 'en-au',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      weekTextShort: 'W',
      todayHint: 'This $0',
      prevHint: 'Previous $0',
      nextHint: 'Next $0',
      viewHint: '$0 view',
      navLinkHint: 'Go to $0',
      moreLinkHint(eventCnt) {
          return `Show ${eventCnt} more event${eventCnt === 1 ? '' : 's'}`;
      },
  };

  var __el$l18 = {
      code: 'el',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4st is the first week of the year.
      },
      prevText: 'Προηγούμενος',
      nextText: 'Επόμενος',
      todayText: 'Σήμερα',
      yearText: 'Ετος',
      monthText: 'Μήνας',
      weekTextLong: 'Εβδομάδα',
      weekTextShort: 'Εβδ',
      dayText: 'Ημέρα',
      listText: 'Ατζέντα',
      allDayText: 'Ολοήμερο',
      moreLinkText: 'περισσότερα',
      noEventsText: 'Δεν υπάρχουν γεγονότα προς εμφάνιση',
  };

  function __de$affix(unitText) {
      return (unitText === 'Tag' || unitText === 'Monat') ? 'r' :
          unitText === 'Jahr' ? 's' : '';
  }
  var __de$l17 = {
      code: 'de',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Zurück',
      nextText: 'Vor',
      todayText: 'Heute',
      yearText: 'Jahr',
      monthText: 'Monat',
      weekTextLong: 'Woche',
      weekTextShort: 'KW',
      dayText: 'Tag',
      listText: 'Terminübersicht',
      allDayText: 'Ganztägig',
      moreLinkText(n) {
          return '+ weitere ' + n;
      },
      noEventsText: 'Keine Ereignisse anzuzeigen',
      prevHint(unitText) {
          return `Vorherige${__de$affix(unitText)} ${unitText}`;
      },
      nextHint(unitText) {
          return `Nächste${__de$affix(unitText)} ${unitText}`;
      },
      todayHint(unitText) {
          // → Heute, Diese Woche, Dieser Monat, Dieses Jahr
          if (unitText === 'Tag') {
              return 'Heute';
          }
          return `Diese${__de$affix(unitText)} ${unitText}`;
      },
      viewHint(unitText) {
          // → Tagesansicht, Wochenansicht, Monatsansicht, Jahresansicht
          const glue = unitText === 'Woche' ? 'n' : unitText === 'Monat' ? 's' : 'es';
          return unitText + glue + 'ansicht';
      },
      navLinkHint: 'Gehe zu $0',
      moreLinkHint(eventCnt) {
          return 'Zeige ' + (eventCnt === 1 ?
              'ein weiteres Ereignis' :
              eventCnt + ' weitere Ereignisse');
      },
      closeHint: 'Schließen',
      eventsHint: 'Ereignisse',
  };

  function __de_at$affix(unitText) {
      return (unitText === 'Tag' || unitText === 'Monat') ? 'r' :
          unitText === 'Jahr' ? 's' : '';
  }
  var __de_at$l16 = {
      code: 'de-at',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Zurück',
      nextText: 'Vor',
      todayText: 'Heute',
      yearText: 'Jahr',
      monthText: 'Monat',
      weekTextLong: 'Woche',
      weekTextShort: 'KW',
      dayText: 'Tag',
      listText: 'Terminübersicht',
      allDayText: 'Ganztägig',
      moreLinkText(n) {
          return '+ weitere ' + n;
      },
      noEventsText: 'Keine Ereignisse anzuzeigen',
      prevHint(unitText) {
          return `Vorherige${__de_at$affix(unitText)} ${unitText}`;
      },
      nextHint(unitText) {
          return `Nächste${__de_at$affix(unitText)} ${unitText}`;
      },
      todayHint(unitText) {
          // → Heute, Diese Woche, Dieser Monat, Dieses Jahr
          if (unitText === 'Tag') {
              return 'Heute';
          }
          return `Diese${__de_at$affix(unitText)} ${unitText}`;
      },
      viewHint(unitText) {
          // → Tagesansicht, Wochenansicht, Monatsansicht, Jahresansicht
          const glue = unitText === 'Woche' ? 'n' : unitText === 'Monat' ? 's' : 'es';
          return unitText + glue + 'ansicht';
      },
      navLinkHint: 'Gehe zu $0',
      moreLinkHint(eventCnt) {
          return 'Zeige ' + (eventCnt === 1 ?
              'ein weiteres Ereignis' :
              eventCnt + ' weitere Ereignisse');
      },
      closeHint: 'Schließen',
      eventsHint: 'Ereignisse',
  };

  var __da$l15 = {
      code: 'da',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Forrige',
      nextText: 'Næste',
      todayText: 'I dag',
      yearText: 'År',
      monthText: 'Måned',
      weekTextLong: 'Uge',
      dayText: 'Dag',
      listText: 'Agenda',
      allDayText: 'Hele\ndagen',
      moreLinkText: 'flere',
      noEventsText: 'Ingen arrangementer at vise',
  };

  var __cy$l14 = {
      code: 'cy',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Blaenorol',
      nextText: 'Nesaf',
      todayText: 'Heddiw',
      yearText: 'Blwyddyn',
      monthText: 'Mis',
      weekTextLong: 'Wythnos',
      dayText: 'Dydd',
      listText: 'Rhestr',
      allDayText: 'Trwy\'r\ndydd',
      moreLinkText: 'Mwy',
      noEventsText: 'Dim digwyddiadau',
  };

  var __cs$l13 = {
      code: 'cs',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Dříve',
      nextText: 'Později',
      todayText: 'Nyní',
      yearText: 'Rok',
      monthText: 'Měsíc',
      weekTextLong: 'Týden',
      weekTextShort: 'Týd',
      dayText: 'Den',
      listText: 'Agenda',
      allDayText: 'Celý den',
      moreLinkText(n) {
          return '+další: ' + n;
      },
      noEventsText: 'Žádné akce k zobrazení',
  };

  var __ca$l12 = {
      code: 'ca',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Anterior',
      nextText: 'Següent',
      todayText: 'Avui',
      yearText: 'Any',
      monthText: 'Mes',
      weekTextLong: 'Setmana',
      weekTextShort: 'Set',
      dayText: 'Dia',
      listText: 'Agenda',
      allDayText: 'Tot\nel dia',
      moreLinkText: 'més',
      noEventsText: 'No hi ha esdeveniments per mostrar',
  };

  var __bs$l11 = {
      code: 'bs',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 7, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'Prošli',
      nextText: 'Sljedeći',
      todayText: 'Danas',
      yearText: 'Godina',
      monthText: 'Mjesec',
      weekTextLong: 'Sedmica',
      weekTextShort: 'Sed',
      dayText: 'Dan',
      listText: 'Raspored',
      allDayText: 'Cijeli\ndan',
      moreLinkText(n) {
          return '+ još ' + n;
      },
      noEventsText: 'Nema događaja za prikazivanje',
  };

  var __bn$l10 = {
      code: 'bn',
      week: {
          dow: 0, // Sunday is the first day of the week.
          doy: 6, // The week that contains Jan 1st is the first week of the year.
      },
      prevText: 'পেছনে',
      nextText: 'সামনে',
      todayText: 'আজ',
      yearText: 'বছর',
      monthText: 'মাস',
      weekTextLong: 'সপ্তাহ',
      dayText: 'দিন',
      listText: 'তালিকা',
      allDayText: 'সারাদিন',
      moreLinkText(n) {
          return '+অন্যান্য ' + n;
      },
      noEventsText: 'কোনো ইভেন্ট নেই',
  };

  var __bg$l9 = {
      code: 'bg',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'назад',
      nextText: 'напред',
      todayText: 'днес',
      yearText: 'година',
      monthText: 'Месец',
      weekTextLong: 'Седмица',
      dayText: 'Ден',
      listText: 'График',
      allDayText: 'Цял ден',
      moreLinkText(n) {
          return '+още ' + n;
      },
      noEventsText: 'Няма събития за показване',
  };

  var __az$l8 = {
      code: 'az',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      prevText: 'Əvvəl',
      nextText: 'Sonra',
      todayText: 'Bu Gün',
      yearText: 'Il',
      monthText: 'Ay',
      weekTextLong: 'Həftə',
      dayText: 'Gün',
      listText: 'Gündəm',
      allDayText: 'Bütün\nGün',
      moreLinkText(n) {
          return '+ daha çox ' + n;
      },
      noEventsText: 'Göstərmək üçün hadisə yoxdur',
  };

  var __ar$l7 = {
      code: 'ar',
      week: {
          dow: 6, // Saturday is the first day of the week.
          doy: 12, // The week that contains Jan 1st is the first week of the year.
      },
      direction: 'rtl',
      prevText: 'السابق',
      nextText: 'التالي',
      todayText: 'اليوم',
      yearText: 'سنة',
      monthText: 'شهر',
      weekTextLong: 'أسبوع',
      dayText: 'يوم',
      listText: 'أجندة',
      allDayText: 'اليوم كله',
      moreLinkText: 'أخرى',
      noEventsText: 'أي أحداث لعرض',
  };

  var __ar_tn$l6 = {
      code: 'ar-tn',
      week: {
          dow: 1, // Monday is the first day of the week.
          doy: 4, // The week that contains Jan 4th is the first week of the year.
      },
      direction: 'rtl',
      prevText: 'السابق',
      nextText: 'التالي',
      todayText: 'اليوم',
      yearText: 'سنة',
      monthText: 'شهر',
      weekTextLong: 'أسبوع',
      dayText: 'يوم',
      listText: 'أجندة',
      allDayText: 'اليوم كله',
      moreLinkText: 'أخرى',
      noEventsText: 'أي أحداث لعرض',
  };

  var __ar_sa$l5 = {
      code: 'ar-sa',
      week: {
          dow: 0, // Sunday is the first day of the week.
          doy: 6, // The week that contains Jan 1st is the first week of the year.
      },
      direction: 'rtl',
      prevText: 'السابق',
      nextText: 'التالي',
      todayText: 'اليوم',
      yearText: 'سنة',
      monthText: 'شهر',
      weekTextLong: 'أسبوع',
      dayText: 'يوم',
      listText: 'أجندة',
      allDayText: 'اليوم كله',
      moreLinkText: 'أخرى',
      noEventsText: 'أي أحداث لعرض',
  };

  var __ar_ma$l4 = {
      code: 'ar-ma',
      week: {
          dow: 6, // Saturday is the first day of the week.
          doy: 12, // The week that contains Jan 1st is the first week of the year.
      },
      direction: 'rtl',
      prevText: 'السابق',
      nextText: 'التالي',
      todayText: 'اليوم',
      yearText: 'سنة',
      monthText: 'شهر',
      weekTextLong: 'أسبوع',
      dayText: 'يوم',
      listText: 'أجندة',
      allDayText: 'اليوم كله',
      moreLinkText: 'أخرى',
      noEventsText: 'أي أحداث لعرض',
  };

  var __ar_ly$l3 = {
      code: 'ar-ly',
      week: {
          dow: 6, // Saturday is the first day of the week.
          doy: 12, // The week that contains Jan 1st is the first week of the year.
      },
      direction: 'rtl',
      prevText: 'السابق',
      nextText: 'التالي',
      todayText: 'اليوم',
      yearText: 'سنة',
      monthText: 'شهر',
      weekTextLong: 'أسبوع',
      dayText: 'يوم',
      listText: 'أجندة',
      allDayText: 'اليوم كله',
      moreLinkText: 'أخرى',
      noEventsText: 'أي أحداث لعرض',
  };

  var __ar_kw$l2 = {
      code: 'ar-kw',
      week: {
          dow: 0, // Sunday is the first day of the week.
          doy: 12, // The week that contains Jan 1st is the first week of the year.
      },
      direction: 'rtl',
      prevText: 'السابق',
      nextText: 'التالي',
      todayText: 'اليوم',
      yearText: 'سنة',
      monthText: 'شهر',
      weekTextLong: 'أسبوع',
      dayText: 'يوم',
      listText: 'أجندة',
      allDayText: 'اليوم كله',
      moreLinkText: 'أخرى',
      noEventsText: 'أي أحداث لعرض',
  };

  var __ar_dz$l1 = {
      code: 'ar-dz',
      week: {
          dow: 0, // Sunday is the first day of the week.
          doy: 4, // The week that contains Jan 1st is the first week of the year.
      },
      direction: 'rtl',
      prevText: 'السابق',
      nextText: 'التالي',
      todayText: 'اليوم',
      yearText: 'سنة',
      monthText: 'شهر',
      weekTextLong: 'أسبوع',
      dayText: 'يوم',
      listText: 'أجندة',
      allDayText: 'اليوم كله',
      moreLinkText: 'أخرى',
      noEventsText: 'أي أحداث لعرض',
  };

  var __af$l0 = {
      code: 'af',
      week: {
          dow: 1, // Maandag is die eerste dag van die week.
          doy: 4, // Die week wat die 4de Januarie bevat is die eerste week van die jaar.
      },
      prevText: 'Vorige',
      nextText: 'Volgende',
      todayText: 'Vandag',
      yearText: 'Jaar',
      monthText: 'Maand',
      weekTextLong: 'Week',
      dayText: 'Dag',
      listText: 'Agenda',
      allDayText: 'Heeldag',
      moreLinkText: 'Addisionele',
      noEventsText: 'Daar is geen gebeurtenisse nie',
  };

  globalLocales.push(
    __af$l0, __ar_dz$l1, __ar_kw$l2, __ar_ly$l3, __ar_ma$l4, __ar_sa$l5, __ar_tn$l6, __ar$l7, __az$l8, __bg$l9, __bn$l10, __bs$l11, __ca$l12, __cs$l13, __cy$l14, __da$l15, __de_at$l16, __de$l17, __el$l18, __en_au$l19, __en_gb$l20, __en_nz$l21, __eo$l22, __es_us$l23, __es$l24, __et$l25, __eu$l26, __fa$l27, __fi$l28, __fr_ca$l29, __fr_ch$l30, __fr$l31, __gl$l32, __he$l33, __hi$l34, __hr$l35, __hu$l36, __hy_am$l37, __id$l38, __is$l39, __it$l40, __ja$l41, __ka$l42, __kk$l43, __km$l44, __ko$l45, __ku$l46, __lb$l47, __lt$l48, __lv$l49, __mk$l50, __ms$l51, __nb$l52, __ne$l53, __nl$l54, __nn$l55, __pl$l56, __pt_br$l57, __pt$l58, __ro$l59, __ru$l60, __si_lk$l61, __sk$l62, __sl$l63, __sm$l64, __sq$l65, __sr_cyrl$l66, __sr$l67, __sv$l68, __ta_in$l69, __th$l70, __tr$l71, __ug$l72, __uk$l73, __uz_cy$l74, __uz$l75, __vi$l76, __zh_cn$l77, __zh_tw$l78, 
  );

})(FullCalendar.Shared);
