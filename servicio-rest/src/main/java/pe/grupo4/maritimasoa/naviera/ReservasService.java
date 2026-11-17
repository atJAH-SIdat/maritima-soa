package pe.grupo4.maritimasoa.naviera;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

/** Lógica de la naviera con datos de prueba en memoria. Los datos se reinician al reiniciar el servicio. */
@Service
public class ReservasService {

	private final Map<String, Viaje> viajes = new LinkedHashMap<>();
	private final Map<String, Boleto> boletos = new LinkedHashMap<>();
	private final AtomicInteger correlativo = new AtomicInteger(0);

	public ReservasService() {
		registrar(new Viaje("MAR-INT-01", "Callao", "Valparaíso", "Chile", "INTERNACIONAL", "PE-CAL",
				LocalDate.of(2026, 11, 28), 25, 180.0));
		registrar(new Viaje("MAR-NAC-02", "Callao", "Salaverry", "Perú", "NACIONAL", "PE-CAL",
				LocalDate.of(2026, 11, 27), 40, 95.0));
		// Zarpa de Matarani, que el servicio SOAP reporta como puerto cerrado.
		registrar(new Viaje("MAR-NAC-03", "Matarani", "Callao", "Perú", "NACIONAL", "PE-MAT",
				LocalDate.of(2026, 11, 29), 30, 110.0));
		// Solo 2 cupos: sirve para probar el rechazo por falta de cupos.
		registrar(new Viaje("MAR-INT-04", "Paita", "Guayaquil", "Ecuador", "INTERNACIONAL", "PE-PAI",
				LocalDate.of(2026, 11, 30), 2, 150.0));
	}

	private void registrar(Viaje viaje) {
		viajes.put(viaje.codigoViaje(), viaje);
	}

	public synchronized Collection<Viaje> listarViajes() {
		return viajes.values().stream().toList();
	}

	public synchronized Viaje buscarViaje(String codigoViaje) {
		Viaje viaje = viajes.get(codigoViaje);
		if (viaje == null) {
			throw new ErrorNegocioException(HttpStatus.NOT_FOUND, "VIAJE_NO_ENCONTRADO",
					"No existe el viaje " + codigoViaje);
		}
		return viaje;
	}

	public synchronized Boleto buscarBoleto(String idBoleto) {
		Boleto boleto = boletos.get(idBoleto);
		if (boleto == null) {
			throw new ErrorNegocioException(HttpStatus.NOT_FOUND, "BOLETO_NO_ENCONTRADO",
					"No existe el boleto " + idBoleto);
		}
		return boleto;
	}

	/** Descuenta los cupos del viaje y emite el boleto. Las dos cosas ocurren juntas o no ocurre ninguna. */
	public synchronized Boleto emitirBoleto(SolicitudBoleto solicitud) {
		validar(solicitud);
		Viaje viaje = buscarViaje(solicitud.codigoViaje());
		int asientos = solicitud.cantidadAsientos();
		if (viaje.cuposDisponibles() < asientos) {
			throw new ErrorNegocioException(HttpStatus.CONFLICT, "SIN_CUPOS",
					"El viaje " + viaje.codigoViaje() + " tiene " + viaje.cuposDisponibles()
							+ " cupos y se solicitaron " + asientos);
		}
		viajes.put(viaje.codigoViaje(), viaje.conCupos(viaje.cuposDisponibles() - asientos));

		String idBoleto = String.format("BOL-2026-%03d", correlativo.incrementAndGet());
		String muelle = "INTERNACIONAL".equals(viaje.tipoRuta()) ? "Muelle B - Internacional" : "Muelle A - Nacional";
		Boleto boleto = new Boleto(idBoleto, viaje.codigoViaje(), solicitud.documentoPasajero().trim(),
				solicitud.nombrePasajero().trim(), viaje.tipoRuta(), asientos,
				solicitud.codigoAutorizacionZarpe().trim(), "EMITIDO", viaje.precioUnitario() * asientos, muelle,
				LocalDateTime.now().truncatedTo(ChronoUnit.SECONDS));
		boletos.put(idBoleto, boleto);
		return boleto;
	}

	private void validar(SolicitudBoleto s) {
		if (s == null || vacio(s.codigoViaje()) || vacio(s.documentoPasajero()) || vacio(s.nombrePasajero())
				|| vacio(s.codigoAutorizacionZarpe())) {
			throw new ErrorNegocioException(HttpStatus.BAD_REQUEST, "SOLICITUD_INVALIDA",
					"Son obligatorios: codigoViaje, documentoPasajero, nombrePasajero y codigoAutorizacionZarpe");
		}
		if (s.cantidadAsientos() == null || s.cantidadAsientos() < 1) {
			throw new ErrorNegocioException(HttpStatus.BAD_REQUEST, "SOLICITUD_INVALIDA",
					"cantidadAsientos debe ser un entero mayor o igual a 1");
		}
	}

	private boolean vacio(String valor) {
		return valor == null || valor.isBlank();
	}
}
