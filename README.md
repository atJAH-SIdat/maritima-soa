# MaritimaSOA

Sistema integrado de venta de pasajes marítimos nacionales e internacionales.
Proyecto integrador del curso **Aplicaciones con Enfoque Orientado a Servicios** (Grupo 4).

## Integrantes

| Integrante | Rol | Carpeta a su cargo |
| --- | --- | --- |
| Albornoz Hinostroza, Jatniel | Arquitecto de procesos (BPMN y jBPM) | `docs/bpmn/`, `jbpm/` |
| Marcelo Rodriguez, Fabian | Desarrollador de servicios (SOAP y REST) | `servicio-soap/`, `servicio-rest/` |
| Vargas Zapata, Renzo | Especialista de integración y pruebas (Mule ESB, ActiveMQ y MUnit) | `mule-esb/` |

## El caso

Una naviera vende pasajes en rutas nacionales (cabotaje) e internacionales (ferris y cruceros). Cada solicitud recorre cinco pasos:

1. **Solicitud de reserva.** El pasajero indica su documento o pasaporte, el código de viaje y la cantidad de asientos.
2. **Consulta de viaje y cupos (REST).** Se obtiene el tipo de ruta, el puerto de origen, los cupos y el precio.
3. **Control portuario y migratorio (SOAP).** Toda ruta verifica que el puerto esté abierto. Solo la ruta internacional valida pasaporte e impedimento de salida.
4. **Emisión del boleto (REST).** Si las validaciones pasan, se descuentan los cupos y se emite el boleto. Si no, se rechaza informando la causa.
5. **Notificación de embarque (ActiveMQ).** El boleto se publica en la cola `cola.embarque.boletos` para generar el pase de embarque.

## Diagrama BPMN

![Proceso de venta de pasajes marítimos](docs/bpmn/venta-pasajes-maritimos.png)

El archivo fuente es [docs/bpmn/venta-pasajes-maritimos.bpmn](docs/bpmn/venta-pasajes-maritimos.bpmn) (BPMN 2.0). Se puede abrir y editar en [bpmn.io](https://demo.bpmn.io) o en Camunda Modeler.

## Componentes

| Componente | Qué hace |
| --- | --- |
| jBPM | Ejecuta el proceso BPMN y evalúa las compuertas. |
| Mule ESB | Bus de integración: endpoint HTTP único, enrutamiento a SOAP y REST, control de excepciones y publicación en ActiveMQ. |
| `AutoridadPortuariaService` (SOAP) | Simula a Capitanía de Puerto y Migraciones. |
| `NavieraReservasAPI` (REST) | Sistema de la naviera: viajes, cupos y boletos. |
| Apache ActiveMQ | Cola `cola.embarque.boletos`. |

## Servicios

### SOAP: `AutoridadPortuariaService`

| Operación | Entrada | Salida |
| --- | --- | --- |
| `consultarEstadoPuerto` | `codigoPuerto`, `fechaZarpe` | `puertoAbierto`, `condicionMaritima`, `codigoAutorizacionZarpe` |
| `validarMigracionPasajero` | `numeroPasaporte`, `documentoIdentidad`, `paisDestino` | `habilitadoViaje`, `pasaporteVigente`, `impedimentoSalida`, `mensajeControl` |

### REST: `NavieraReservasAPI`

| Método y ruta | Entrada | Salida |
| --- | --- | --- |
| `GET /api/viajes` | Ninguna | Lista de todos los viajes |
| `GET /api/viajes/{codigoViaje}` | `codigoViaje` en la ruta | `codigoViaje`, `origen`, `destino`, `paisDestino`, `tipoRuta`, `codigoPuerto`, `fechaZarpe`, `cuposDisponibles`, `precioUnitario` |
| `POST /api/boletos` | `codigoViaje`, `documentoPasajero`, `nombrePasajero`, `tipoRuta`, `cantidadAsientos`, `codigoAutorizacionZarpe` | `idBoleto`, `codigoViaje`, `estado`, `montoTotal`, `muelleEmbarque`, `fechaEmision` |
| `GET /api/boletos/{idBoleto}` | `idBoleto` en la ruta | Detalle del boleto y su estado |

Los errores del servicio REST responden con el JSON `{"codigo": "...", "mensaje": "..."}`:

| HTTP | `codigo` | Cuándo ocurre |
| --- | --- | --- |
| 400 | `SOLICITUD_INVALIDA` | Falta un campo obligatorio, `cantidadAsientos` es menor que 1 o el JSON está mal formado |
| 404 | `VIAJE_NO_ENCONTRADO` | El código de viaje no existe |
| 404 | `BOLETO_NO_ENCONTRADO` | El id de boleto no existe |
| 409 | `SIN_CUPOS` | Se piden más asientos que los cupos disponibles |

## Estructura del repositorio

```
maritima-soa/
├── README.md
├── docs/bpmn/        Diagrama BPMN (.bpmn, .png, .svg) y su generador
├── servicio-rest/    NavieraReservasAPI, Spring Boot, puerto 8082
├── servicio-soap/    AutoridadPortuariaService, Spring Boot + Spring WS, puerto 8083
├── pruebas/postman/  Colección de Postman para el servicio REST
├── pruebas/soapui/   Mensajes de prueba para el servicio SOAP
├── mule-esb/         Flujo Mule y pruebas MUnit (Entregable 3)
└── jbpm/             Proceso en jBPM            (Entregable 3)
```

## Cómo ejecutar los servicios

### Requisitos

- JDK 17 o superior (probado con JDK 25). Verificar con `java -version`.
- Conexión a internet la primera vez, para que Maven descargue las dependencias.
- No hace falta instalar Maven: cada servicio trae su Maven Wrapper (`mvnw`).
- Puertos 8082 y 8083 libres.

### 1. Servicio REST `NavieraReservasAPI` (puerto 8082)

En una terminal:

```bash
cd servicio-rest
mvnw.cmd spring-boot:run        # Windows
./mvnw spring-boot:run          # Linux o macOS
```

Está listo cuando la consola muestra `Started NavieraReservasApplication`. Comprobar en el navegador: <http://localhost:8082/api/viajes>

### 2. Servicio SOAP `AutoridadPortuariaService` (puerto 8083)

En otra terminal:

```bash
cd servicio-soap
mvnw.cmd spring-boot:run        # Windows
./mvnw spring-boot:run          # Linux o macOS
```

Está listo cuando la consola muestra `Started AutoridadPortuariaApplication`. Comprobar en el navegador el WSDL: <http://localhost:8083/ws/autoridadPortuaria.wsdl>

### Alternativas

- **Desde Spring Tool Suite:** File > Import > Existing Maven Projects, elegir la carpeta del servicio y luego Run As > Spring Boot App.
- **Como JAR:** `mvnw.cmd -DskipTests package` y luego `java -jar target/servicio-rest-1.0.0.jar` (o `servicio-soap-1.0.0.jar`).

Los dos servicios guardan sus datos en memoria. Al reiniciarlos, los cupos y boletos vuelven a su estado inicial.

## Datos de prueba

### Viajes (servicio REST)

| `codigoViaje` | Ruta | `tipoRuta` | `codigoPuerto` | `fechaZarpe` | Cupos | Precio | Sirve para probar |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `MAR-INT-01` | Callao a Valparaíso (Chile) | `INTERNACIONAL` | `PE-CAL` | 2026-11-28 | 25 | 180.0 | Venta internacional exitosa |
| `MAR-NAC-02` | Callao a Salaverry | `NACIONAL` | `PE-CAL` | 2026-11-27 | 40 | 95.0 | Venta nacional exitosa |
| `MAR-NAC-03` | Matarani a Callao | `NACIONAL` | `PE-MAT` | 2026-11-29 | 30 | 110.0 | Rechazo por puerto cerrado |
| `MAR-INT-04` | Paita a Guayaquil (Ecuador) | `INTERNACIONAL` | `PE-PAI` | 2026-11-30 | 2 | 150.0 | Rechazo por falta de cupos |

### Puertos y pasaportes (servicio SOAP)

| `codigoPuerto` | Condición | ¿Abierto? |
| --- | --- | --- |
| `PE-CAL` (Callao) | `NORMAL` | Sí |
| `PE-PAI` (Paita) | `NORMAL` | Sí |
| `PE-MAT` (Matarani) | `OLEAJE_ANOMALO` | No |
| Cualquier otro | `PUERTO_NO_REGISTRADO` | No |

| `numeroPasaporte` | Situación | `habilitadoViaje` |
| --- | --- | --- |
| `PE1234567` | Vigente, sin impedimento | `true` |
| `PE7654321` | Vencido | `false` |
| `PE5555555` | Vigente, con impedimento de salida | `false` |
| Cualquier otro | No registrado | `false` |

## Cómo probar

### Servicio REST con Postman

1. Iniciar el servicio REST (si ya estaba en uso, reiniciarlo para tener los cupos iniciales).
2. En Postman: Import > elegir `pruebas/postman/NavieraReservasAPI.postman_collection.json`.
3. Abrir la colección y pulsar Run para ejecutar las 8 peticiones en orden.

| # | Petición | Resultado esperado |
| --- | --- | --- |
| 1 | `GET /api/viajes` | 200, lista de 4 viajes |
| 2 | `GET /api/viajes/MAR-INT-01` | 200, `tipoRuta` = `INTERNACIONAL` |
| 3 | `GET /api/viajes/MAR-XXX-99` | 404, `VIAJE_NO_ENCONTRADO` |
| 4 | `POST /api/boletos` (2 asientos en `MAR-INT-01`) | 201, `estado` = `EMITIDO`, `montoTotal` = 360.0 |
| 5 | `GET /api/boletos/{idBoleto}` del boleto anterior | 200, mismo boleto |
| 6 | `POST /api/boletos` (3 asientos en `MAR-INT-04`, que tiene 2) | 409, `SIN_CUPOS` |
| 7 | `POST /api/boletos` con `cantidadAsientos` = 0 | 400, `SOLICITUD_INVALIDA` |
| 8 | `GET /api/boletos/BOL-0000-000` | 404, `BOLETO_NO_ENCONTRADO` |

### Servicio SOAP con SoapUI

1. Iniciar el servicio SOAP.
2. En SoapUI: File > New SOAP Project.
3. En Initial WSDL escribir `http://localhost:8083/ws/autoridadPortuaria.wsdl` y aceptar. SoapUI crea las dos operaciones con una petición de ejemplo cada una.
4. Abrir la petición, reemplazar los `?` por los datos de la tabla y pulsar el botón verde. También se puede pegar el contenido de los archivos de `pruebas/soapui/`.

| # | Archivo en `pruebas/soapui/` | Operación y datos | Resultado esperado |
| --- | --- | --- | --- |
| 1 | `01-consultarEstadoPuerto-abierto.xml` | `consultarEstadoPuerto`: `PE-CAL`, 2026-11-28 | `puertoAbierto` = `true`, `codigoAutorizacionZarpe` = `ZARPE-PE-CAL-20261128` |
| 2 | `02-consultarEstadoPuerto-cerrado.xml` | `consultarEstadoPuerto`: `PE-MAT`, 2026-11-29 | `puertoAbierto` = `false`, `condicionMaritima` = `OLEAJE_ANOMALO` |
| 3 | `03-validarMigracion-habilitado.xml` | `validarMigracionPasajero`: `PE1234567` | `habilitadoViaje` = `true` |
| 4 | `04-validarMigracion-pasaporte-vencido.xml` | `validarMigracionPasajero`: `PE7654321` | `habilitadoViaje` = `false`, `pasaporteVigente` = `false` |
| 5 | `05-validarMigracion-impedimento-salida.xml` | `validarMigracionPasajero`: `PE5555555` | `habilitadoViaje` = `false`, `impedimentoSalida` = `true` |

### Prueba rápida sin herramientas

```bash
curl http://localhost:8082/api/viajes/MAR-INT-01

curl -H "Content-Type: text/xml" --data-binary @pruebas/soapui/01-consultarEstadoPuerto-abierto.xml http://localhost:8083/ws
```

## Herramientas

- JDK 17 o superior y Spring Boot 4.1.2 para los servicios
- Anypoint Studio y Mule Runtime para el flujo de integración (Entregable 3)
- Apache ActiveMQ
- jBPM
- SoapUI y Postman para las pruebas
