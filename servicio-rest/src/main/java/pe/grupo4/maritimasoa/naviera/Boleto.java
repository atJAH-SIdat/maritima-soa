package pe.grupo4.maritimasoa.naviera;

import java.time.LocalDateTime;

/** Boleto emitido. */
public record Boleto(
		String idBoleto,
		String codigoViaje,
		String documentoPasajero,
		String nombrePasajero,
		String tipoRuta,
		int cantidadAsientos,
		String codigoAutorizacionZarpe,
		String estado,
		double montoTotal,
		String muelleEmbarque,
		LocalDateTime fechaEmision) {
}
