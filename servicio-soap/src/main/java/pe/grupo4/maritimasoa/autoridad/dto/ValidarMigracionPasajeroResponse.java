package pe.grupo4.maritimasoa.autoridad.dto;

import jakarta.xml.bind.annotation.XmlAccessType;
import jakarta.xml.bind.annotation.XmlAccessorType;
import jakarta.xml.bind.annotation.XmlRootElement;
import jakarta.xml.bind.annotation.XmlType;

@XmlRootElement(name = "validarMigracionPasajeroResponse")
@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "", propOrder = { "habilitadoViaje", "pasaporteVigente", "impedimentoSalida", "mensajeControl" })
public class ValidarMigracionPasajeroResponse {

	private boolean habilitadoViaje;
	private boolean pasaporteVigente;
	private boolean impedimentoSalida;
	private String mensajeControl;

	public ValidarMigracionPasajeroResponse() {
	}

	public ValidarMigracionPasajeroResponse(boolean pasaporteVigente, boolean impedimentoSalida,
			String mensajeControl) {
		this.pasaporteVigente = pasaporteVigente;
		this.impedimentoSalida = impedimentoSalida;
		this.habilitadoViaje = pasaporteVigente && !impedimentoSalida;
		this.mensajeControl = mensajeControl;
	}

	public boolean isHabilitadoViaje() {
		return habilitadoViaje;
	}

	public boolean isPasaporteVigente() {
		return pasaporteVigente;
	}

	public boolean isImpedimentoSalida() {
		return impedimentoSalida;
	}

	public String getMensajeControl() {
		return mensajeControl;
	}
}
