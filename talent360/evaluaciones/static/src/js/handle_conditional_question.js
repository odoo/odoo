document.querySelectorAll('input[name="preguntas_desbloqueadas"]').forEach(function(element) {
    var preguntas_desbloqueadas = element.value.replace(/[\[\]]/g, '').split(',');
    preguntas_desbloqueadas.forEach(function(pregunta) {
        var preguntaElement = document.querySelector("[id='" + pregunta.trim() + "']");
        if (preguntaElement) {
            preguntaElement.style.display = "none";
            preguntaElement.querySelectorAll('input[required], textarea[required], select[required]').forEach(function(field) {
                field.removeAttribute('required');
            });
        }
    });
});

document.querySelectorAll('.o_survey_form_choice_item').forEach(function(input) {
    input.addEventListener('change', function(event) {
        var userAnswer = this.value;
        var preguntaId = this.name.split('_')[0];
        var preguntaElement = document.getElementById(preguntaId);

        if (preguntaElement && preguntaElement.dataset.respuestaTrigger) {
            var respuesta_trigger = preguntaElement.dataset.respuestaTrigger;
            var preguntas_desbloqueadas = preguntaElement.dataset.preguntasDesbloqueadas.replace(/[\[\]]/g, '').split(',');

            if (userAnswer == respuesta_trigger) {
                desbloquear_preguntas(preguntas_desbloqueadas);
            } else {
                preguntas_desbloqueadas.forEach(function(preguntaDesbloqueadaId) {
                    var preguntaDesbloqueadaElement = document.getElementById(preguntaDesbloqueadaId.trim());
                    if (preguntaDesbloqueadaElement) {
                        preguntaDesbloqueadaElement.style.display = "none";
                        preguntaDesbloqueadaElement.querySelectorAll('input[required], textarea[required], select[required]').forEach(function(field) {
                            field.removeAttribute('required');
                        });
                    }
                });
            }
        }
    });
});


function desbloquear_preguntas(preguntas) {
    preguntas.forEach(function(pregunta) {
        var preguntaElement = document.querySelector("[id='" + pregunta.trim() + "']");
        if (preguntaElement) {
            preguntaElement.style.display = "block";
            preguntaElement.querySelectorAll('input, textarea, select').forEach(function(field) {
                field.setAttribute('required', '');
            });
        }
    });
}