document.querySelectorAll('input[name="preguntas_desbloqueadas"]').forEach(function(element) {
    var preguntas_desbloqueadas = element.value.replace(/[\[\]]/g, '').split(',');
    preguntas_desbloqueadas.forEach(function(pregunta) {
        var preguntaElement = document.querySelector("[id='" + pregunta + "']");
        if (preguntaElement) {
            preguntaElement.style.display = "none";
        }
    });
});

// Escucha los cambios en los elementos de entrada
document.querySelectorAll('.o_survey_form_choice_item').forEach(function(input) {
    input.addEventListener('change', function(event) {
        var userAnswer = event.target.value;
        var respuesta_trigger = document.querySelector('input[name="respuesta_trigger"]').value;

        // Compara la respuesta del usuario con respuesta_trigger
        if (userAnswer == respuesta_trigger) {
            document.querySelectorAll('input[name="preguntas_desbloqueadas"]').forEach(function(element) {
                var preguntas_desbloqueadas = element.value.replace(/[\[\]]/g, '').split(',');
                unlockAdditionalQuestions(preguntas_desbloqueadas);
            });
        } else {
            document.querySelectorAll('input[name="preguntas_desbloqueadas"]').forEach(function(element) {
                var preguntas_desbloqueadas = element.value.replace(/[\[\]]/g, '').split(',');
                preguntas_desbloqueadas.forEach(function(pregunta) {
                    var preguntaElement = document.querySelector("[id='" + pregunta + "']");
                    if (preguntaElement) {
                        preguntaElement.style.display = "none";
                    }
                });
            });
        }
    });
});

function unlockAdditionalQuestions(preguntas) {
    // Desbloquea las preguntas adicionales
    preguntas.forEach(function(pregunta) {
        var preguntaElement = document.querySelector("[id='" + pregunta + "']");
        if (preguntaElement) {
            preguntaElement.style.display = "block";
        }
    });
}