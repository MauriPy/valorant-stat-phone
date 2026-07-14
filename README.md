# Valorant Stat Phone

Producto vendible: celular 3D + ESP32-C3 + OLED que muestra el KDA de la **ultima partida** del comprador.

## Arquitectura

```
Comprador                    Tu nube                         Datos
---------                    -------                         -----
ESP32 + OLED  --WiFi-->  Backend FastAPI  -->  Tracker Network API
       |                      |              o  Riot API + RSO
       |                 Web /setup
       +-- WiFiManager (1a vez)
       +-- Codigo emparejamiento en OLED
```

### Flujo del comprador

1. Enciende el dispositivo → se abre portal WiFi `ValorantPhone-Setup`.
2. Configura su WiFi de casa.
3. El OLED muestra un **codigo de 6 caracteres**.
4. Abre `https://tu-dominio.com/setup?code=XXXXXX`.
5. Pulsa **Iniciar sesion con Riot** (opt-in obligatorio para producto comercial).
6. El OLED actualiza el KDA cada ~3 minutos.

## Estructura

```
backend/          API + web de configuracion (FastAPI)
firmware/         ESP32-C3 + SSD1306 (PlatformIO)
```

## Backend (desarrollo local)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # edita claves
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Prueba: http://localhost:8000/health

### Proveedor de datos

En `.env`:

| Variable | Valor | Cuando usarlo |
|----------|-------|---------------|
| `STATS_PROVIDER=tracker` | Tracker Network | Mas rapido para lanzar; pide API en [tracker.gg/developers](https://tracker.gg/developers) |
| `STATS_PROVIDER=riot` | Riot RSO + API | Camino oficial a largo plazo; requiere production key |

## Firmware

1. Instala [PlatformIO](https://platformio.org/).
2. Copia `firmware/valorant-phone/include/config.h.example` → `config.h`.
3. Pon la IP/URL de tu backend en `API_BASE_URL`.
4. Compila y flashea:

```bash
cd firmware/valorant-phone
pio run -t upload
```

## Endpoints principales

| Metodo | Ruta | Quien |
|--------|------|-------|
| POST | `/api/devices/register` | ESP32 (1a vez) |
| GET | `/api/devices/{id}/stats` | ESP32 (polling) |
| GET | `/setup?code=ABC123` | Comprador (web) |
| GET | `/auth/riot/login` | Comprador (RSO) |

## Pasos para vender legalmente

1. **Dominio + HTTPS** (Let's Encrypt en VPS o Railway/Fly.io).
2. **API comercial**: solicita acceso en Tracker Network **o** production key + RSO en Riot.
3. **Legal**: Terminos de servicio, politica de privacidad, disclaimer "no oficial".
4. **Marca**: no uses logos de Riot/Valorant sin permiso.
5. **Soporte**: reset de fabrica (borrar NVS), FAQ WiFi, OTA updates.

## Costes estimados (inicio)

| Item | Coste aprox. |
|------|----------------|
| VPS / hosting | 5-20 EUR/mes |
| Tracker API | segun plan TRN |
| ESP32-C3 + OLED | 5-10 EUR/unidad |
| Impresion 3D | variable |

## Proximos pasos sugeridos

- [ ] Solicitar API en tracker.gg/developers
- [ ] Desplegar backend en produccion con HTTPS
- [ ] Probar flujo completo con tu ESP32
- [ ] Disenar carcasa 3D con ventana para OLED
- [ ] Anadir OTA y boton reset en hardware
