package pe.grupo4.maritimasoa.naviera;

import java.net.URI;
import java.util.Collection;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** NavieraReservasAPI: viajes, cupos y boletos. */
@RestController
@RequestMapping("/api")
public class NavieraController {

	private final ReservasService servicio;

	public NavieraController(ReservasService servicio) {
		this.servicio = servicio;
	}

	@GetMapping("/viajes")
	public Collection<Viaje> listarViajes() {
		return servicio.listarViajes();
	}

	@GetMapping("/viajes/{codigoViaje}")
	public Viaje consultarViaje(@PathVariable String codigoViaje) {
		return servicio.buscarViaje(codigoViaje);
	}

	@PostMapping("/boletos")
	public ResponseEntity<Boleto> emitirBoleto(@RequestBody SolicitudBoleto solicitud) {
		Boleto boleto = servicio.emitirBoleto(solicitud);
		return ResponseEntity.created(URI.create("/api/boletos/" + boleto.idBoleto())).body(boleto);
	}

	@GetMapping("/boletos/{idBoleto}")
	public Boleto consultarBoleto(@PathVariable String idBoleto) {
		return servicio.buscarBoleto(idBoleto);
	}
}
