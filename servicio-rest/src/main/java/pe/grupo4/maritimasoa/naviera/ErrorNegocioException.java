package pe.grupo4.maritimasoa.naviera;

import org.springframework.http.HttpStatus;

/** Error de negocio con el código HTTP y el código de error que se devuelve al cliente. */
public class ErrorNegocioException extends RuntimeException {

	private final HttpStatus estado;
	private final String codigo;

	public ErrorNegocioException(HttpStatus estado, String codigo, String mensaje) {
		super(mensaje);
		this.estado = estado;
		this.codigo = codigo;
	}

	public HttpStatus getEstado() {
		return estado;
	}

	public String getCodigo() {
		return codigo;
	}
}
