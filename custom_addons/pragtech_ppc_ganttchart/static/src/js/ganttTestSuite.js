function enqueueNewTest() {
  var test = ganttTestUnits.shift();
  if (!test)
    return;


  //ci si registra per gli eventi di refresh

  ge.element.one("gantt.refreshGanttCompleted", function () {
    //si registra l'evento di validazione al refresh
    ge.element.one("gantt.refreshGanttCompleted", function () {
      if (test.assertOk())
        console.debug("------------------------- OK!");
      else
        console.error("------------------------- FAILED!");

      //si passa al test successivo
      setTimeout(enqueueNewTest, 200);
      //enqueueNewTest();
    });

    //si chiama la funzione di preparazione del test
    console.debug("Test \""+test.name+"\"");
    test.prepareTest();
  });


  //se nel test ci sono i task si resetta il gantt
  if (test.tasks) {
    //si resetta tutto
    ge.reset();

    //si prepara un progetto
    var prj = {
      tasks:                      test.tasks,
      resources:                  [],
      roles:                      [],
      //permessi
      canWriteOnParent:           true,
      canWrite:                   true,
      canAdd:                     true,
      canInOutdent:               true,
      canMoveUpDown:              true,
      canSeePopEdit:              true,
      canSeeFullEdit:             true,
      canSeeDep:                  true,
      canSeeCriticalPath:         true,
      canAddIssue:                false,
      cannotCloseTaskIfIssueOpen: false
    };

    //si carica il progetto
    ge.loadProject(prj);


    // se i task non ci sono si parte dallo stato lasciato dall'ultimo test
  } else {
    //si lancia l'evento facendo finta di avere caricato tutti itask
    ge.element.trigger("gantt.refreshGanttCompleted");
  }

}


$(function () {
  console.debug("Gantt test unit activated");
  $("#workSpace").one("gantt.refreshGanttCompleted", function () {
    setTimeout(enqueueNewTest, 1000);
  });
});


//---------------------------------------------------------------------  TEST UNIT DEFINITIONS ------------------------------------------------------------------------------------

var ganttTestUnits = [];

//--------------------------------------------------------------------------------------------------------------
ganttTestUnits.push({name: "Passo 1: Chiudi P chiude F",
  tasks:                   [
    {"id": "616", "name": "test", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "GTU", "level": 0, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1473976800000, "duration": 3, "end": 1474408799999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#3BBF67", "tags": "", "startDate": "16/09/2016", "endDate": "20/09/2016", "lastModified": 1474028638447, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "canAddIssue": true, "hasChild": true},
    {"id": "tmp_fk1474274262872", "name": "P", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1473976800000, "duration": 1, "end": 1474063199999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": true},
    {"id": "tmp_fk1474274277068", "name": "F", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 2, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1473976800000, "duration": 1, "end": 1474063199999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false}
  ],
  prepareTest:             function () {
    //apro il selettore stati e chiudo il task
    ge.tasks[1].rowElement.find(".taskStatus").click().oneTime(100, "setStat", function () {$(this).next().find("[status=STATUS_DONE]").click()});
  },
  assertOk:                function () {
    var ret = ge.tasks[1].status == "STATUS_DONE" && ge.tasks[2].status == "STATUS_DONE";
    return ret;
  }
});

ganttTestUnits.push({name: "Passo 2: Provo ad aprire P, non ci riesco",
  prepareTest:             function () {
    //apro il selettore stati e chiudo il task
    ge.tasks[2].rowElement.find(".taskStatus").click().oneTime(100, "setStat", function () {$(this).next().find("[status=STATUS_ACTIVE]").click()});
  },
  assertOk:                function () {
    return ret = ge.tasks[1].status == "STATUS_DONE" && ge.tasks[2].status == "STATUS_DONE";
  }
});

ganttTestUnits.push({name: "Passo 3: Fallisce P fallisce F",
  prepareTest:             function () {
    //apro il selettore stati e chiudo il task
    ge.tasks[1].rowElement.find(".taskStatus").click().oneTime(100, "setStat", function () {$(this).next().find("[status=STATUS_FAILED]").click()});
  },
  assertOk:                function () {
    return ret = ge.tasks[1].status == "STATUS_FAILED";
  }
});

ganttTestUnits.push({name: "Passo 4: Apro P, F resta fallito",
  prepareTest:             function () {
    //apro il selettore stati e chiudo il task
    ge.tasks[1].rowElement.find(".taskStatus").click().oneTime(100, "setStat", function () {$(this).next().find("[status=STATUS_ACTIVE]").click()});
  },
  assertOk:                function () {
    return ret = ge.tasks[2].status == "STATUS_FAILED";
  }
});


//------------------------------------------------------------------------------------
ganttTestUnits.push({name: "Indenta figlio sotto padre chiuso: chiude figlio",
  tasks:                   [
    {"id": "624", "name": "test", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T624", "level": 0, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#3BBF67", "tags": "", "startDate": "19/09/2016", "endDate": "19/09/2016", "lastModified": 1474279210280, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "canAddIssue": true, "hasChild": true},
    {"id": "tmp_fk1474279215599", "name": "p", "progress": 100, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_DONE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp_fk1474279220599", "name": "f", "progress": 100, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false}
  ],
  prepareTest:             function () {
    ge.currentTask = ge.tasks[2];
    ge.indentCurrentTask();
  },
  assertOk:                function () {
    //il figlio deve diventare chiuso
    return ge.tasks[2].status == "STATUS_DONE";
  }
});


//------------------------------------------------------------------------------------
ganttTestUnits.push({name: "Crea 2 dip da task aperto con lag diversi: C->suspended, c.start max lag ",
  tasks:                   [
    {"id": "624", "name": "test", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T624", "level": 0, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#3BBF67", "tags": "", "startDate": "19/09/2016", "endDate": "19/09/2016", "lastModified": 1474279210280, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "canAddIssue": true, "hasChild": true},
    {"id": "tmp_fk1474279215599", "name": "a", "progress": 100, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp_fk1474279220599", "name": "b", "progress": 100, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp_fk1474279220449", "name": "c", "progress": 100, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false}
  ],
  prepareTest:             function () {
    ge.tasks[3].rowElement.find("[name=depends]").val("2:1,3:2").blur();
  },
  assertOk:                function () {
    //il figlio deve diventare chiuso, la root si deve allargare e c deve usare il lag massimo
    return ge.tasks[3].status == "STATUS_SUSPENDED" && ge.tasks[0].duration == 4 && new Date(ge.tasks[2].end).distanceInWorkingDays(new Date(ge.tasks[3].start)) == 3;
  }
});


//------------------------------------------------------------------------------------
ganttTestUnits.push({name: "Crea dipendenza da task chiuso: mette B in stato aperto",
  tasks:                   [
    {"id": "624", "name": "test", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T624", "level": 0, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#3BBF67", "tags": "", "startDate": "19/09/2016", "endDate": "19/09/2016", "lastModified": 1474279210280, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "canAddIssue": true, "hasChild": true},
    {"id": "tmp_fk1474279215599", "name": "a", "progress": 100, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_DONE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp_fk1474279220599", "name": "b", "progress": 100, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_SUSPENDED", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false}
  ],
  prepareTest:             function () {
    ge.tasks[2].rowElement.find("[name=depends]").val("2").blur();
  },
  assertOk:                function () {
    //il figlio deve diventare chiuso
    return ge.tasks[2].status == "STATUS_ACTIVE";
  }
});


//------------------------------------------------------------------------------------
ganttTestUnits.push({name: "Chiude A : mette B e C in stato aperto",
  tasks:                   [
    {"id": "624", "name": "test", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T624", "level": 0, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 2, "end": 1474408799999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#3BBF67", "tags": "", "startDate": "19/09/2016", "endDate": "19/09/2016", "lastModified": 1474279210280, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "canAddIssue": true, "hasChild": true},
    {"id": "tmp_fk1474292364588", "name": "a", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp_fk1474292366844", "name": "b", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_SUSPENDED", "depends": "2", "canWrite": true, "start": 1474322400000, "duration": 1, "end": 1474408799999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp_fk1474292368291", "name": "c", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_SUSPENDED", "depends": "2", "canWrite": true, "start": 1474322400000, "duration": 1, "end": 1474408799999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false}
  ],
  prepareTest:             function () {
    //apro il selettore stati e clicco su done
    ge.tasks[1].rowElement.find(".taskStatus").click().oneTime(100, "setStat", function () {$(this).next().find("[status=STATUS_DONE]").click()});
  },
  assertOk:                function () {
    //"a" devere andare in completato
    return ge.tasks[1].status == "STATUS_DONE" && ge.tasks[2].status == "STATUS_ACTIVE" && ge.tasks[3].status == "STATUS_ACTIVE";
  }
});


//------------------------------------------------------------------------------------
ganttTestUnits.push({name: "Tree tutto undefined, apro la root: A open B,C suspended",
  tasks:                   [
    {"id": "624", "name": "test", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T624", "level": 0, "status": "STATUS_UNDEFINED", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 3, "end": 1474495199999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#3BBF67", "tags": "", "startDate": "19/09/2016", "endDate": "19/09/2016", "lastModified": 1474279210280, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "canAddIssue": true, "hasChild": true},
    {"id": "tmp_fk1474292364588", "name": "a", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_UNDEFINED", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp_fk1474292366844", "name": "b", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_UNDEFINED", "depends": "2", "canWrite": true, "start": 1474322400000, "duration": 1, "end": 1474408799999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp_fk1474292368291", "name": "c", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_UNDEFINED", "depends": "3", "canWrite": true, "start": 1474408800000, "duration": 1, "end": 1474495199999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false}
  ],
  prepareTest:             function () {
    //apro il selettore stati e clicco su done
    ge.tasks[0].rowElement.find(".taskStatus").click().oneTime(100, "setStat", function () {$(this).next().find("[status=STATUS_ACTIVE]").click()});
  },
  assertOk:                function () {
    //"a" devere andare in completato
    return ge.tasks[0].status == "STATUS_ACTIVE" && ge.tasks[1].status == "STATUS_ACTIVE" && ge.tasks[2].status == "STATUS_SUSPENDED" && ge.tasks[3].status == "STATUS_SUSPENDED";
  }
});


//------------------------------------------------------------------------------------
ganttTestUnits.push({name: "Caso Cabassi passo 1: c dipende da a, c1 dipende da b1: si deve poter chiudere b1",
  tasks:                   [
    {"id": "624", "name": "test", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T624", "level": 0, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 4, "end": 1474581599999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#3BBF67", "tags": "", "startDate": "19/09/2016", "endDate": "19/09/2016", "lastModified": 1474279210280, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "canAddIssue": true, "hasChild": true},
    {"id": "tmp_fk1474293219659", "name": "a", "progress": 100, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp_fk1474293221523", "name": "b", "progress": 100, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": true},
    {"id": "tmp_1474293309413", "name": "b1", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 2, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp_fk1474293224322", "name": "c", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_SUSPENDED", "depends": "2", "canWrite": true, "start": 1474322400000, "duration": 2, "end": 1474495199999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": true},
    {"id": "tmp_fk1474293224858", "name": "c1", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 2, "status": "STATUS_SUSPENDED", "depends": "4", "canWrite": true, "start": 1474322400000, "duration": 1, "end": 1474408799999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false}
  ],
  prepareTest:             function () {
    //apro il selettore stati e clicco su done
    ge.tasks[3].rowElement.find(".taskStatus").click().oneTime(100, "setStat", function () {$(this).next().find("[status=STATUS_DONE]").click()});
  },
  assertOk:                function () {
    //"b1" devere andare in completato c e c1 in sospeso
    return ge.tasks[3].status == "STATUS_DONE" && ge.tasks[4].status == "STATUS_SUSPENDED" && ge.tasks[5].status == "STATUS_SUSPENDED";
  }
});


ganttTestUnits.push({name: "Caso Cabassi passo 2: c dipende da a, c1 dipende da b1: chiudendo a c e c1 divengono attivi",
  prepareTest:             function () {
    //apro il selettore stati e clicco su done
    ge.tasks[1].rowElement.find(".taskStatus").click().oneTime(100, "setStat", function () {$(this).next().find("[status=STATUS_DONE]").click()});
  },
  assertOk:                function () {
    //a done, c,c1 attivi
    return ge.tasks[1].status == "STATUS_DONE" && ge.tasks[4].status == "STATUS_ACTIVE" && ge.tasks[5].status == "STATUS_ACTIVE";
  }
});


ganttTestUnits.push({name: "Caso Cabassi passo 3: Fallisco predecessore, dip e figli falliscono. a->failed: c,c1->failed",
  prepareTest:             function () {
    //apro il selettore stati e clicco su done
    ge.tasks[1].rowElement.find(".taskStatus").click().oneTime(100, "setStat", function () {$(this).next().find("[status=STATUS_FAILED]").click()});
  },
  assertOk:                function () {
    //a done, c,c1 attivi
    return ge.tasks[1].status == "STATUS_FAILED" && ge.tasks[4].status == "STATUS_FAILED" && ge.tasks[5].status == "STATUS_FAILED";
  }
});


//------------------------------------------------------------------------------------
ganttTestUnits.push({name: "Test durate: indenta b(2gg) sotto a(1gg): root -> 3gg, a->2gg, c prende la stessa fine di b",
  tasks:                   [
    {"id": "624", "name": "test", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T624", "level": 0, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 2, "end": 1474408799999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#3BBF67", "tags": "", "startDate": "19/09/2016", "endDate": "19/09/2016", "lastModified": 1474279210280, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "canAddIssue": true, "hasChild": true},
    {"id": "tmp_fk1474296996877", "name": "a", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 1, "end": 1474322399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp_fk1474297003163", "name": "b", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1474236000000, "duration": 2, "end": 1474408799999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp_fk1474297024666", "name": "c", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_SUSPENDED", "depends": "2", "canWrite": true, "start": 1474322400000, "duration": 1, "end": 1474408799999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false}
  ],
  prepareTest:             function () {
    //indento b
    ge.currentTask = ge.tasks[2];
    ge.indentCurrentTask();
  },
  assertOk:                function () {
    //root -> 3gg, a->2gg, c prende la stessa fine di b
    return ge.tasks[0].duration == 3 && ge.tasks[1].duration == 2 && new Date(ge.tasks[2].end).distanceInWorkingDays(new Date(ge.tasks[3].start)) == 1;
  }
});


//------------------------------------------------------------------------------------
ganttTestUnits.push({name: "Loop indentando b1 sotto b: candidato figlio con dip che coinvolgono il futuro padre. Deve rimuovere la dip da b1 ad a",
  tasks:                   [
    {"id":"745", "name": "test loop", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T745", "level": 0, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1476136800000, "duration": 6, "end": 1476827999999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#3BBF67", "tags": "", "startDate": "11/10/2016", "endDate": "18/10/2016", "lastModified": 1476259070239, "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "canAddIssue": true, "hasChild": true},
    {"id": "tmp1", "name": "a", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T745.01.02", "level": 1, "status": "STATUS_SUSPENDED", "depends": "4", "canWrite": true, "start": 1476655200000, "duration": 1, "end": 1476741599999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#F9C154", "startDate": "17/10/2016", "endDate": "17/10/2016", "lastModified": 1476259070261, "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "parentId": "746", "canAddIssue": true, "hasChild": false},
    {"id": "tmp2", "name": "b", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T745.02", "level": 1, "status": "STATUS_SUSPENDED", "depends": "2", "canWrite": true, "start": 1476741600000, "duration": 1, "end": 1476827999999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#F9C154", "startDate": "18/10/2016", "endDate": "18/10/2016", "lastModified": 1476259070268, "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "parentId": "745", "canAddIssue": true, "hasChild": false},
    {"id": "tmp3", "name": "b1", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T745.03", "level": 1, "status": "STATUS_SUSPENDED", "depends": "", "canWrite": true, "start": 1476396000000, "duration": 1, "end": 1476482399999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#F9C154", "startDate": "14/10/2016", "endDate": "14/10/2016", "lastModified": 1476259070275, "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "parentId": "745", "canAddIssue": true, "hasChild": false}
  ],
  prepareTest:             function () {
    //indento b
    ge.currentTask = ge.tasks[3];
    ge.indentCurrentTask();
  },
  assertOk:                function () {
    //deve aver indentato b1, ma rimosso le dip
    return ge.tasks[3].level == 2 && ge.tasks[1].depends=="";
  }
});

//------------------------------------------------------------------------------------
ganttTestUnits.push({name: "Cambio le dipendenze di C mettendo lag -> A e B devono restare chiusi",
    tasks: [
    {"id": "844", "name": "altro test", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T844", "level": 0, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1477346400000, "duration": 5, "end": 1477954799999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#3BBF67", "tags": "", "startDate": "25/10/2016", "endDate": "31/10/2016", "lastModified": 1477385116247, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "canAddIssue": true, "hasChild": true},
    {"id": "tmp1", "name": "A", "progress": 100, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T844.01", "level": 1, "status": "STATUS_DONE", "depends": "", "canWrite": true, "start": 1477346400000, "duration": 1, "end": 1477432799999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#6EBEF4", "startDate": "25/10/2016", "endDate": "25/10/2016", "lastModified": 1477385116257, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "parentId": "844", "canAddIssue": true, "hasChild": false},
    {"id": "tmp2", "name": "B", "progress": 100, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T844.02", "level": 1, "status": "STATUS_DONE", "depends": "2", "canWrite": true, "start": 1477432800000, "duration": 1, "end": 1477519199999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#6EBEF4", "startDate": "26/10/2016", "endDate": "26/10/2016", "lastModified": 1477385116263, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "parentId": "844", "canAddIssue": true, "hasChild": false},
    {"id": "tmp3", "name": "C", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T844.03", "level": 1, "status": "STATUS_ACTIVE", "depends": "2", "canWrite": true, "start": 1477432800000, "duration": 1, "end": 1477519199999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#3BBF67", "startDate": "26/10/2016", "endDate": "26/10/2016", "lastModified": 1477385116273, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "parentId": "844", "canAddIssue": true, "hasChild": false}
    ],
  prepareTest:             function () {
    //indento b
    ge.tasks[3].rowElement.find("[name=depends]").val("2:1").blur();
  },
  assertOk:                function () {
    //deve aver lasciato A e B chiusi
    return ge.tasks[1].status=="STATUS_DONE" && ge.tasks[2].status=="STATUS_DONE";
  }
});



//------------------------------------------------------------------------------------
ganttTestUnits.push({name: "Pan/Move nel caso di un figlio F con dipendenze ad uno 'zio' Z. Sposto avanti R -> P mantiene la durata",
  tasks:                   [
    {"id": "1134", "name": "Root", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "T1134", "level": 0, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1480374000000, "duration": 2, "end": 1480546799999, "startIsMilestone": false, "endIsMilestone": false, "collapsed": false, "assigs": [], "loadComplete": false, "statusColor": "#3BBF67", "tags": "", "startDate": "01/12/2016", "endDate": "01/12/2016", "lastModified": 1480593817093, "lastModifier": "System Manager", "totalIssues": 0, "openIssues": 0, "budget": 0, "totalCosts": 0, "totalWorklog": 0, "totalEstimated": 0, "canAddIssue": true, "hasChild": true, "unchanged": false},
    {"id": "tmp1", "name": "Z", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1480374000000, "duration": 1, "end": 1480460399999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false},
    {"id": "tmp2", "name": "P", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 1, "status": "STATUS_ACTIVE", "depends": "", "canWrite": true, "start": 1480374000000, "duration": 2, "end": 1480546799999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": true},
    {"id": "tmp3", "name": "F", "progress": 0, "progressByWorklog": false, "relevance": 0, "type": "", "typeId": "", "description": "", "code": "", "level": 2, "status": "STATUS_SUSPENDED", "depends": "2", "canWrite": true, "start": 1480460400000, "duration": 1, "end": 1480546799999, "startIsMilestone": false, "endIsMilestone": false, "assigs": [], "hasChild": false}
  ],

prepareTest:             function () {
  //Sposto R
  var r=ge.tasks[0];
  var d=Date.parseString(r.rowElement.find("[name=start]").val());
  d.incrementDateByWorkingDays(1);
  r.rowElement.find("[name=start]").val(d.format()).blur();
},
assertOk:                function () {
  //deve aver lasciato A e B chiusi
  return ge.tasks[0].duration==2 && ge.tasks[2].duration==2;
}
});


//ganttTestUnits=ganttTestUnits.slice(0,2)
//ganttTestUnits=[ganttTestUnits[5]]

// esegue sono ultimo test
//ganttTestUnits = [ganttTestUnits[ganttTestUnits.length - 1]]
