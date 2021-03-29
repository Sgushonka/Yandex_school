Важная(нет) инофрмация!
	Проектом предусмотрен дополнитьельный обработчик(добавлялся для тестирования на сервере)

	POST /delete/all/records
		Принимает JSON,если в нем присутствует ключ "delete_all" - удаляет ВСЕ записи из БД


Инструкция по развертке REST_API:
1)по SSH логинимся нв виртуальную машину (пароль выдан ботом)

2)Настройка сервера.Далее будет представлен листинг команд и описание их сути
sudo apt-get update (обновляем текущие пакеты)
sudo apt install ufw (устанавливаем фаервол (ufw - Uncomplicated Firewall))
sudo ufw default allow outgoing
sudo ufw default deny incoming
sudo ufw allow ssh (разрешаем логиниться по ssh)
sudo ufw allow 5000 (разрешаем тестовый порт flask)
sudo ufw enable

3) Закидываем рабочую папку проекта на машину (я сделал через WinSCP)

4) Устанавливаем pip и venv
sudo apt install python3-pip
sudo apt install python3-venv

5)Создадим и активируем вирт. среду
python3 -m venv Shop_api/venv
source venv/bin/activate

6)Установим все неоходимые пакеты, содержащиеся в requirements.txt
pip install -r requirements.txt

7)Протестируем работу API на тестовом сервере.

8)Устанвливаем nginx и gunicorn
sudo apt install nginx
pip install gunicorn

9)Обновим конфигурацию nginx так, чтобы он переадресовывал запросы на gunicorn
sudo rm /etc/nginx/sites-enable/default
sudo nano /etc/nginx/sites-enable/shop_api	  
	server {
		listen 80;
		server_name 130.193.41.157;

		location / {
			proxy_pass http://127.0.0.1:8080;
			include /etc/nginx/proxy_params;
			proxy_redirect off;
		}
	}
	
10)Добавим разрешения на http/tcp трафик и удалим тестовый порт, перезапустим nginx
sudo ufw delete allow 5000
sudo ufw allow http/tcp
sudo ufw enable
sudo systemctl restart nginx

11)запустим gunicorn yf 8080 с количеством "рабочих" равным (2*количество ядер) + 1
gunicorn -b 127.0.0.1:8080 -w 9 run:app

12) Если все выше сработало, установим и настроим supervisor(автоматический запуск и перезапуск gunicorn)
sudo apt install supervisor
sudo nano /etc/supervisor/conf.d/shop_api.conf

	[program:shop_api]
	directory=/home/entrant/Shop_api
	command=/home/entrant/Shop_api/venv/bin/gunicorn -b 127.0.0.1:8080 -w 9 run:app
	user=entrant
	autostart=true
	autorestart=true
	stopasgroup=true
	killasgroup=true
	stderr_logfile=/var/log/shop_api/shop_api.err.log
	stdout_logfile=/var/log/shop_api/shop_api.out.log

sudo supervisorctl reload

13) Вроде все :)