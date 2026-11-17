package pe.grupo4.maritimasoa.autoridad;

import java.util.Map;

import org.springframework.ws.server.endpoint.annotation.Endpoint;
import org.springframework.ws.server.endpoint.annotation.PayloadRoot;
import org.springframework.ws.server.endpoint.annotation.RequestPayload;
import org.springframework.ws.server.endpoint.annotation.ResponsePayload;

import pe.grupo4.maritimasoa.autoridad.dto.ConsultarEstadoPuertoRequest;
import pe.grupo4.maritimasoa.autoridad.dto.ConsultarEstadoPuertoResponse;
import pe.grupo4.maritimasoa.autoridad.dto.ValidarMigracionPasajeroRequest;
import pe.grupo4.maritimasoa.autoridad.dto.ValidarMigracionPasajeroResponse;

/**
 * AutoridadPortuariaService: simula a Capitanía de Puerto y a Migraciones con datos de prueba en memoria.
 */
@Endpoint
public class AutoridadPortuariaEndpoint {

	/** Puertos registrados: código y condición marítima del día. Solo NORMAL permite zarpar. */
	private static final Map<String, String> PUERTOS = Map.of(
			"PE-CAL", "NORMAL",
			"PE-PAI", "NORMAL",
			"PE-MAT", "OLEAJE_ANOMALO");

	private record Pasaporte(boolean vigente, boolean impedimentoSalida) {
	}

	private static final Map<String, Pasaporte> PASAPORTES = Map.of(
			"PE1234567", new Pasaporte(true, false),
			"PE7654321", new Pasaporte(false, false),
			"PE5555555", new Pasaporte(true, true));

	@PayloadRoot(namespace = WebServiceConfig.NAMESPACE, localPart = "consultarEstadoPuertoRequest")
	@ResponsePayload
	public ConsultarEstadoPuertoResponse consultarEstadoPuerto(@RequestPayload ConsultarEstadoPuertoRequest request) {
		String codigoPuerto = limpiar(request.getCodigoPuerto());
		String condicion = PUERTOS.get(codigoPuerto);
		if (condicion == null) {
			return new ConsultarEstadoPuertoResponse(false, "PUERTO_NO_REGISTRADO", null);
		}
		if (!"NORMAL".equals(condicion)) {
			return new ConsultarEstadoPuertoResponse(false, condicion, null);
		}
		String fecha = limpiar(request.getFechaZarpe()).replace("-", "");
		return new ConsultarEstadoPuertoResponse(true, condicion, "ZARPE-" + codigoPuerto + "-" + fecha);
	}

	@PayloadRoot(namespace = WebServiceConfig.NAMESPACE, localPart = "validarMigracionPasajeroRequest")
	@ResponsePayload
	public ValidarMigracionPasajeroResponse validarMigracionPasajero(
			@RequestPayload ValidarMigracionPasajeroRequest request) {
		String numero = limpiar(request.getNumeroPasaporte());
		Pasaporte pasaporte = PASAPORTES.get(numero);
		if (pasaporte == null) {
			return new ValidarMigracionPasajeroResponse(false, false, "Pasaporte " + numero + " no registrado");
		}
		if (!pasaporte.vigente()) {
			return new ValidarMigracionPasajeroResponse(false, false, "Pasaporte vencido");
		}
		if (pasaporte.impedimentoSalida()) {
			return new ValidarMigracionPasajeroResponse(true, true, "El pasajero tiene impedimento de salida del país");
		}
		return new ValidarMigracionPasajeroResponse(true, false,
				"Pasajero habilitado para viajar a " + limpiar(request.getPaisDestino()));
	}

	private String limpiar(String valor) {
		return valor == null ? "" : valor.trim();
	}
}
