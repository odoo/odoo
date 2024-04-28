console.log("handle_response_clima.js");

// Función que se ejecuta al hacer click en el botón de enviar
function handleResponseClima() {
    // Recoge todos los inputs de tipo radio
    var radios = document.querySelectorAll('.o_survey_form_choice_item');
    var selectedValues = {};
    radios.forEach(function(radio) {
        if (radio.checked) {
            var questionId = radio.value.split('-')[0];
            selectedValues[questionId] = radio.value.split('-')[1];
        }
    });

    // Recoge todos los elementos textarea
    var textareas = document.querySelectorAll('.o_survey_question_text_box');
    var textareaValues = {};
    textareas.forEach(function(textarea) {
        var questionId = textarea.name.split('_')[1];
        textareaValues[questionId] = textarea.value;
    });

    console.log(selectedValues);
    console.log(textareaValues);
}

// Envía los valores seleccionados a la base de datos
// var xhr = new XMLHttpRequest();
// xhr.open('POST', '/ruta/a/tu/servidor', true);
// xhr.setRequestHeader('Content-Type', 'application/json');
// xhr.send(JSON.stringify(selectedValues));