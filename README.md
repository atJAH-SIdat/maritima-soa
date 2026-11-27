# MaritimaSOA

Sistema integrado de venta de pasajes marítimos nacionales e internacionales.
Proyecto integrador del curso **Aplicaciones con Enfoque Orientado a Servicios** (Grupo 4).

## Integrantes

| Integrante | Rol | Carpeta a su cargo |
| --- | --- | --- |
| Marcelo Rodriguez, Fabian | Arquitecto de procesos (BPMN y jBPM) | `docs/bpmn/`, `jbpm/` |
| Vargas Zapata, Renzo | Desarrollador de servicios (SOAP y REST) | `servicio-soap/`, `servicio-rest/` |
| Albornoz Hinostroza, Jatniel | Especialista de integración y pruebas (Mule ESB, ActiveMQ y MUnit) | `mule-esb/` |

## El caso

Una naviera vende pasajes en rutas nacionales (cabotaje) e internacionales (ferris y cruceros). Cada solicitud recorre cinco pasos:

1. **Solicitud de reserva.** El pasajero indica su documento o pasaporte, el código de viaje y la cantidad de asientos.
2. **Consulta de viaje y cupos (REST).** Se obtiene el tipo de ruta, el puerto de origen, los cupos y el precio.
3. **Control portuario y migratorio (SOAP).** Toda ruta verifica que el puerto esté abierto. Solo la ruta internacional valida pasaporte e impedimento de salida.
4. **Emisión del boleto (REST).** Si las validaciones pasan, se descuentan los cupos y se emite el boleto. Si no, se rechaza informando la causa.
5. **Notificación de embarque (ActiveMQ).** El boleto se publica en la cola `cola.embarque.boletos` y Despacho genera el pase de embarque.

## Arquitectura

```
                              ┌──────────────────────────────────────┐
  Cliente (Postman) ─POST────►│ Mule ESB :8081  venta-pasajes-flow   │──► REST  :8082  NavieraReservasAPI
                  /api/ventas │  excepciones de negocio (422/400)    │──► SOAP  :8083  AutoridadPortuariaService
                              │  excepción técnica (503)             │──► ActiveMQ :61616  cola.embarque.boletos
                              └──────────────────────────────────────┘                │
                                                                                      ▼
  Business Central ──────────►┌──────────────────────────────────────┐     despacho-embarque-flow (Mule)
  (tareas humanas)            │ jBPM :8080  venta-pasajes-maritimos  │──►  genera el pase de embarque
                              │  compuertas = reglas del negocio     │──► REST :8082, SOAP :8083,
                              └──────────────────────────────────────┘     ActiveMQ :61613 (STOMP)
```

- **Mule ESB** es el punto de entrada para sistemas: recibe la venta, habla con cada servicio en su protocolo, controla las excepciones y publica el aviso de embarque. También consume la cola como Despacho.
- **jBPM** ejecuta el mismo proceso de negocio con personas: el pasajero llena la solicitud en una tarea humana y recibe su boleto en otra. Sus tareas llaman a los mismos servicios y publican en la misma cola.

## Diagrama BPMN (versión final)

![Proceso de venta de pasajes marítimos](docs/bpmn/venta-pasajes-maritimos.png)

| Archivo | Para qué sirve |
| --- | --- |
| [jbpm/venta-pasajes-maritimos.bpmn](jbpm/venta-pasajes-maritimos.bpmn) | **Proceso ejecutable** en jBPM 7: variables, condiciones de las compuertas, tareas humanas y tareas que llaman a los servicios |
| [docs/bpmn/venta-pasajes-maritimos.bpmn](docs/bpmn/venta-pasajes-maritimos.bpmn) | Modelo de documentación (BPMN 2.0); se abre en [bpmn.io](https://demo.bpmn.io) o Camunda Modeler |
| `docs/bpmn/venta-pasajes-maritimos.png` / `.svg` | Imagen del diagrama |

Los dos archivos tienen los mismos 4 carriles, 4 compuertas de decisión, 2 de unión y 3 eventos de fin. Así se corresponde cada tarea con lo implementado:

| Tarea del BPMN | En jBPM | En Mule (`venta-pasajes-flow`) |
| --- | --- | --- |
| Solicitar reserva de pasaje | Tarea humana `SolicitarReserva` (asignada a `wbadmin`) | `HTTP Listener` POST `/api/ventas` |
| Consultar viaje y cupos | Tarea que llama a `GET :8082/api/viajes/{codigo}` | `HTTP Request` "Consultar viaje" |
| ¿Hay cupos? | Compuerta: `cuposDisponibles >= cantidadAsientos` | `Choice` + `Raise Error APP:SIN_CUPOS` |
| Consultar estado del puerto | Tarea que llama al SOAP `consultarEstadoPuerto` | `Web Service Consumer` |
| ¿Puerto abierto? | Compuerta: `puertoAbierto` | `Choice` + `Raise Error APP:PUERTO_CERRADO` |
| ¿Tipo de ruta? | Compuerta: `tipoRuta == "INTERNACIONAL"` | `Choice` |
| Validar migración del pasajero | Tarea que llama al SOAP `validarMigracionPasajero` | `Web Service Consumer` |
| ¿Habilitado para viajar? | Compuerta: `habilitadoViaje` | `Choice` + `Raise Error APP:MIGRACION_RECHAZADA` |
| Emitir boleto y descontar cupos | Tarea que llama a `POST :8082/api/boletos` | `HTTP Request` "Emitir boleto" |
| Publicar aviso de embarque | Tarea que publica en `cola.embarque.boletos` (STOMP) | `JMS Publish` |
| Generar pase de embarque | Tarea que arma el código del pase | `despacho-embarque-flow` (`JMS Listener`) |
| Notificar rechazo | Tareas que marcan `estado = RECHAZADA` | `On Error Continue` (422) |
| Recibir boleto y pase de embarque | Tarea humana `RecibirBoleto` | Respuesta HTTP 201 |

## Componentes

| Componente | Puerto | Qué hace |
| --- | --- | --- |
| `NavieraReservasAPI` (REST) | 8082 | Sistema de la naviera: viajes, cupos y boletos |
| `AutoridadPortuariaService` (SOAP) | 8083 | Simula a la Capitanía de Puerto y a Migraciones |
| Apache ActiveMQ | 61616 (OpenWire), 61613 (STOMP), 8161 (consola) | Cola `cola.embarque.boletos` |
| Mule ESB (`venta-pasajes-maritimos`) | 8081 | Flujo de integración, excepciones y consumidor de Despacho |
| jBPM (Business Central) | 8080 | Ejecuta el proceso BPMN con sus tareas humanas |

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

### Mule ESB: `POST /api/ventas` (puerto 8081)

Petición:

```json
{
  "codigoViaje": "MAR-INT-01",
  "cantidadAsientos": 2,
  "documentoPasajero": "71234567",
  "nombrePasajero": "Ana Perez",
  "numeroPasaporte": "PE1234567"
}
```

`numeroPasaporte` solo se usa en rutas internacionales. Respuesta de una venta exitosa (201):

```json
{
  "estado": "EMITIDO",
  "idBoleto": "BOL-2026-001",
  "codigoViaje": "MAR-INT-01",
  "tipoRuta": "INTERNACIONAL",
  "cantidadAsientos": 2,
  "montoTotal": 360,
  "muelleEmbarque": "Muelle B - Internacional",
  "avisoEmbarque": "PUBLICADO"
}
```

### Manejo de excepciones en Mule

| Tipo | Errores | Cómo se maneja | Respuesta |
| --- | --- | --- | --- |
| **Negocio** | `APP:SIN_CUPOS`, `APP:PUERTO_CERRADO`, `APP:MIGRACION_RECHAZADA`, `APP:VIAJE_NO_ENCONTRADO`, `APP:EMISION_RECHAZADA`, lanzados con `Raise Error` | `On Error Continue` | 422 `{"estado": "RECHAZADA", "causa": "...", "mensaje": "..."}` |
| **Solicitud incompleta** | `APP:SOLICITUD_INVALIDA` | `On Error Continue` | 400 con la misma estructura |
| **Técnica** | `WSC:CANNOT_DISPATCH`, `WSC:CONNECTIVITY`, `WSC:TIMEOUT`, `HTTP:CONNECTIVITY`, `HTTP:TIMEOUT` (un servicio no responde) | `On Error Propagate` | 503 `{"estado": "ERROR", "causa": "SERVICIO_NO_DISPONIBLE"}`; no se emite boleto |
| **ActiveMQ caído** | `JMS:CONNECTIVITY`, `JMS:PUBLISHING` | `Try` + `On Error Continue` | 201: el boleto ya emitido no se pierde y `avisoEmbarque` = `PENDIENTE` |

Las direcciones de los servicios y el nombre de la cola están en [maritima.properties](mule-esb/venta-pasajes-maritimos/src/main/resources/maritima.properties), no escritos en el flujo.

## Estructura del repositorio

```
maritima-soa/
├── README.md
├── docs/bpmn/                       Diagrama BPMN de documentación (.bpmn, .png, .svg)
├── servicio-rest/                   NavieraReservasAPI, Spring Boot, puerto 8082
├── servicio-soap/                   AutoridadPortuariaService, Spring Boot + Spring WS, puerto 8083
├── mule-esb/venta-pasajes-maritimos/
│   ├── src/main/mule/               venta-pasajes.xml (flujos) y global.xml (configuraciones)
│   ├── src/main/resources/          maritima.properties y el contrato wsdl/autoridadPortuaria.wsdl
│   └── src/test/munit/              venta-pasajes-test-suite.xml (4 pruebas MUnit)
├── jbpm/                            Proceso ejecutable venta-pasajes-maritimos.bpmn y su generador
├── pruebas/postman/                 Colecciones de Postman: servicio REST y flujo Mule
└── pruebas/soapui/                  Mensajes de prueba para el servicio SOAP
```

## Cómo ejecutar el proyecto

### Requisitos

| Herramienta | Versión probada | Java que usa |
| --- | --- | --- |
| Servicios REST y SOAP | Spring Boot 4.1.2 | JDK 17 o superior (probado con JDK 25) |
| Apache ActiveMQ Classic | 6.4.0 | JDK 17 o superior |
| Anypoint Studio | 7 con Mule 4.13 | El JDK 17 que trae Studio |
| jBPM | 7.74.1.Final (distribución servidor) | **JDK 8** (con JDK 11 o superior falla Business Central) |
| Postman y SoapUI | | |

Conviene abrir una ventana de cmd por componente, cada una con su propio `JAVA_HOME`.

### Orden de arranque

1. ActiveMQ
2. Servicio REST
3. Servicio SOAP
4. Mule (necesita ActiveMQ encendido: si no lo encuentra, la aplicación no se despliega)
5. jBPM

### 1. ActiveMQ (61616, consola en 8161)

jBPM publica en la cola por STOMP, que viene desactivado. Una sola vez, en `C:\activemq\conf\activemq.xml`, quitar `<!--` y `-->` de la línea del conector `stomp`:

```xml
<transportConnector name="stomp" uri="stomp://0.0.0.0:61613?maximumConnections=1000&amp;wireFormat.maxFrameSize=10485760"/>
```

Iniciar con un JDK 17 o superior:

```bat
cd C:\activemq\bin
activemq start
```

Está listo cuando muestra `Connector stomp started` y `Apache ActiveMQ ... started`. Consola: <http://localhost:8161/admin> (usuario `admin`, contraseña `admin`), pestaña **Queues**.

### 2. Servicio REST `NavieraReservasAPI` (puerto 8082)

```bash
cd servicio-rest
mvnw.cmd spring-boot:run        # Windows
./mvnw spring-boot:run          # Linux o macOS
```

Está listo cuando la consola muestra `Started NavieraReservasApplication`. Comprobar en el navegador: <http://localhost:8082/api/viajes>

### 3. Servicio SOAP `AutoridadPortuariaService` (puerto 8083)

```bash
cd servicio-soap
mvnw.cmd spring-boot:run        # Windows
./mvnw spring-boot:run          # Linux o macOS
```

Está listo cuando la consola muestra `Started AutoridadPortuariaApplication`. Comprobar el WSDL: <http://localhost:8083/ws/autoridadPortuaria.wsdl>

Alternativas para los dos servicios:

- **Desde Spring Tool Suite:** File > Import > Existing Maven Projects, elegir la carpeta del servicio y luego Run As > Spring Boot App.
- **Como JAR:** `mvnw.cmd -DskipTests package` y luego `java -jar target/servicio-rest-1.0.0.jar` (o `servicio-soap-1.0.0.jar`).

Los dos servicios guardan sus datos en memoria. Al reiniciarlos, los cupos y boletos vuelven a su estado inicial.

### 4. Mule ESB (puerto 8081)

1. En Anypoint Studio 7: File > Import > Anypoint Studio > **Anypoint Studio project from File System** y elegir `mule-esb/venta-pasajes-maritimos`.
2. Clic derecho sobre el proyecto > Run As > **Mule Application**.
3. Está listo cuando la consola muestra `venta-pasajes-maritimos ... DEPLOYED`.

En el lienzo se ven dos flujos:

- `venta-pasajes-flow` lleva la venta de punta a punta. Para que se lea de un vistazo, cada etapa es un subflujo que se llama con Flow Reference: `validar-solicitud`, `consultar-viaje`, `consultar-puerto`, `migraciones`, `emitir-boleto`, `publicar-aviso` y `responder-venta`. Los subflujos no tienen manejador propio: los errores vuelven al flujo principal, que responde 400, 422 o 503.
- `despacho-embarque-flow` consume la cola y genera el pase de embarque.

Cada paso deja en la consola una línea `[MaritimaSOA] ...`.

### 5. jBPM (Business Central en 8080)

1. Iniciar jBPM con el JDK 8:

   ```bat
   set JAVA_HOME=C:\Java\jdk8
   set PATH=%JAVA_HOME%\bin;%PATH%
   cd C:\jbpm\bin
   standalone.bat
   ```

2. Entrar a <http://localhost:8080/business-central> (usuario `wbadmin`, contraseña `wbadmin`).
3. Crear el proyecto `maritima-soa` en MySpace e **Importar activos** el archivo `jbpm/venta-pasajes-maritimos.bpmn`, con el paquete `com.myspace.maritima_soa`.
4. Abrir el proceso, menú de formularios > **Generar todos los formularios** y guardar.
5. En el proyecto, pulsar **Implementar**.
6. Menú > Gestionar > Definiciones de procesos > `venta-pasajes-maritimos` > **Iniciar** (el formulario de inicio se envía vacío).
7. Menú > Seguimiento > Bandeja de tareas > **SolicitarReserva** > Iniciar, llenar los datos y Completar.
8. Aparece **RecibirBoleto** con el número de boleto, el monto y el pase de embarque. Completarla.

En la ventana de cmd de jBPM cada llamada deja una línea `[MaritimaSOA] ...`. El camino recorrido se ve en Gestionar > Instancias de procesos > la instancia > Diagrama.

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

`documentoPasajero` y `nombrePasajero` son libres.

## Cómo probar

### Flujo Mule con Postman

1. Encender ActiveMQ, REST, SOAP y Mule. Reiniciar el servicio REST antes para tener los cupos iniciales.
2. En Postman: Import > `pruebas/postman/MaritimaSOA-Mule.postman_collection.json` y pulsar Run.

| # | Datos | Resultado esperado |
| --- | --- | --- |
| 1 | `MAR-INT-01`, 2 asientos, `PE1234567` | 201, `EMITIDO`, `montoTotal` 360, `avisoEmbarque` `PUBLICADO` |
| 2 | `MAR-NAC-02`, 1 asiento | 201, `EMITIDO`, sin control migratorio |
| 3 | `MAR-INT-01`, `PE7654321` | 422, `MIGRACION_RECHAZADA` (pasaporte vencido) |
| 4 | `MAR-INT-01`, `PE5555555` | 422, `MIGRACION_RECHAZADA` (impedimento de salida) |
| 5 | `MAR-NAC-03` | 422, `PUERTO_CERRADO` (oleaje anómalo) |
| 6 | `MAR-INT-04`, 3 asientos | 422, `SIN_CUPOS` |
| 7 | `MAR-XXX-99` | 422, `VIAJE_NO_ENCONTRADO` |
| 8 | `cantidadAsientos` 0 | 400, `SOLICITUD_INVALIDA` |

Excepciones técnicas:

| Prueba | Resultado esperado |
| --- | --- |
| Apagar el servicio SOAP y enviar la petición 2 | 503, `SERVICIO_NO_DISPONIBLE` (`WSC:CANNOT_DISPATCH`); no se emite boleto |
| Apagar ActiveMQ con Mule ya iniciado y enviar la petición 2 | 201, boleto emitido con `avisoEmbarque` = `PENDIENTE` |

Después de las ventas exitosas, en la consola de ActiveMQ la cola `cola.embarque.boletos` muestra los mensajes encolados y consumidos, y en la consola de Mule aparece `[MaritimaSOA] Despacho: pase de embarque PASE-BOL-... generado`.

### Pruebas MUnit

Los servicios se simulan con `Mock When`, así que no hace falta encender nada.

- **En Anypoint Studio:** clic derecho sobre `src/test/munit/venta-pasajes-test-suite.xml` > Run MUnit suite.
- **Por consola**, con el Maven y el JDK que trae Studio (el Maven 3.10 no es compatible con el plugin de Mule):

  ```bat
  set JAVA_HOME=C:\AnypointStudio\plugins\org.mule.tooling.jdk.v17.win32.x86_64_1.6.2
  cd mule-esb\venta-pasajes-maritimos
  C:\AnypointStudio\plugins\org.mule.tooling.maven.dist_7.29.1.202610230228\apache-maven-3.9.15\bin\mvn.cmd test
  ```

| Prueba | Se simula | Se valida |
| --- | --- | --- |
| `venta-internacional-exitosa-test` | Viaje con cupos, puerto abierto, pasaporte habilitado, boleto emitido | `estado` = `EMITIDO`, monto 360.0, HTTP 201 y 1 publicación en la cola |
| `pasaporte-vencido-test` | Migraciones responde `habilitadoViaje` = `false` | `RECHAZADA`, causa `MIGRACION_RECHAZADA`, HTTP 422; no se llamó a "Emitir boleto" ni a la cola |
| `sin-cupos-test` | Viaje con 2 cupos y se piden 3 | causa `SIN_CUPOS`, HTTP 422; no se llamó al SOAP |
| `servicio-soap-caido-test` | El SOAP lanza `WSC:CANNOT_DISPATCH` | El error se propaga (no se oculta) |

### Proceso en jBPM

| Datos en SolicitarReserva | Camino del proceso |
| --- | --- |
| `MAR-INT-01`, 2, `PE1234567` | Venta exitosa: boleto emitido y aviso publicado en la cola |
| `MAR-NAC-02`, 1, pasaporte vacío | Venta exitosa sin pasar por Migraciones |
| `MAR-INT-01`, 1, `PE7654321` | Venta rechazada (control migratorio) |
| `MAR-NAC-03`, 1 | Venta rechazada (puerto cerrado) |
| `MAR-INT-04`, 3, `PE1234567` | Venta rechazada (sin cupos) |

Si un servicio está apagado, la instancia queda en error con el mensaje "El servicio ... no responde". Si ActiveMQ está apagado, la venta termina y el aviso queda como `NO_PUBLICADO`.

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

curl -H "Content-Type: application/json" -d "{\"codigoViaje\":\"MAR-NAC-02\",\"cantidadAsientos\":1,\"documentoPasajero\":\"45678912\",\"nombrePasajero\":\"Luis Rojas\"}" http://localhost:8081/api/ventas
```

## Problemas frecuentes

| Síntoma | Causa | Solución |
| --- | --- | --- |
| Business Central no carga y la consola repite un aviso 405 | jBPM se inició con JDK 11 o superior | Detener, borrar `standalone\tmp`, `standalone\data` y `deployments\*.failed`, e iniciar con JDK 8 |
| ActiveMQ muestra `UnsupportedClassVersionError` | Se inició con JDK 8 u 11 | Iniciarlo con JDK 17 o superior |
| jBPM deja el aviso como `NO_PUBLICADO` | STOMP desactivado en ActiveMQ | Activar el conector `stomp` (paso 1) y reiniciar ActiveMQ |
| La aplicación Mule no se despliega: `Could not connect to broker URL` | ActiveMQ estaba apagado al iniciar Mule | Encender ActiveMQ y volver a ejecutar la aplicación |
| `mvn` falla con `NoSuchMethodError ... DefaultMirrorSelector` | Maven 3.10 no es compatible con el plugin de Mule | Usar el Maven 3.9 que trae Anypoint Studio |

## Herramientas

- JDK 17 o superior y Spring Boot 4.1.2 para los servicios
- Anypoint Studio 7 con Mule 4.13, MUnit 3.7 y los conectores HTTP 1.12, Web Service Consumer 2.2 y JMS 2.0
- Apache ActiveMQ Classic 6.4
- jBPM 7.74 con JDK 8
- SoapUI y Postman para las pruebas
