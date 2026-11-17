package pe.grupo4.maritimasoa.naviera;

import java.util.LinkedHashMap;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/** Convierte los errores en una respuesta JSON uniforme: {"codigo": "...", "mensaje": "..."}. */
@RestControllerAdvice
public class ManejadorErrores {

	@ExceptionHandler(ErrorNegocioException.class)
	public ResponseEntity<Map<String, String>> errorNegocio(ErrorNegocioException ex) {
		return respuesta(ex.getEstado(), ex.getCodigo(), ex.getMessage());
	}

	@ExceptionHandler(HttpMessageNotReadableException.class)
	public ResponseEntity<Map<String, String>> jsonInvalido(HttpMessageNotReadableException ex) {
		return respuesta(HttpStatus.BAD_REQUEST, "SOLICITUD_INVALIDA", "El cuerpo de la solicitud no es un JSON válido");
	}

	private ResponseEntity<Map<String, String>> respuesta(HttpStatus estado, String codigo, String mensaje) {
		Map<String, String> cuerpo = new LinkedHashMap<>();
		cuerpo.put("codigo", codigo);
		cuerpo.put("mensaje", mensaje);
		return ResponseEntity.status(estado).body(cuerpo);
	}
}
