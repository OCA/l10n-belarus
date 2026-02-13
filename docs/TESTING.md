# Тестирование модулей l10n-belarus

## Быстрый запуск тестов

### Запустить все тесты модуля

```bash
cd /Users/zubik/www/artcloud/ai/odoo/OCA/l10n-belarus

# Первый запуск (создаст контейнеры)
docker compose -f docker-compose.test.yml up --abort-on-container-exit

# Последующие запуски
docker compose -f docker-compose.test.yml up --abort-on-container-exit

# Удалить контейнеры и данные после тестирования
docker compose -f docker-compose.test.yml down -v
```

### Запустить только конкретный тест

```bash
docker compose -f docker-compose.test.yml run --rm odoo_test \
  odoo -d odoo_test \
  --test-tags=currency_rate_update_by_nbb.test_currency_rate_update_nbrb \
  --stop-after-init \
  --log-level=test
```

### Запустить только один тестовый метод

```bash
docker compose -f docker-compose.test.yml run --rm odoo_test \
  odoo -d odoo_test \
  --test-tags=currency_rate_update_by_nbb.test_currency_rate_update_nbrb::TestCurrencyRateUpdateNBRB::test_obtain_rates_byn_base \
  --stop-after-init \
  --log-level=test
```

## Проверка code style (pre-commit)

```bash
# Установить pre-commit (один раз)
pip3 install pre-commit

# Запустить проверки
cd /Users/zubik/www/artcloud/ai/odoo/OCA/l10n-belarus
pre-commit run --all-files

# Или установить git hook (будет проверять при каждом коммите)
pre-commit install
```

## Отладка тестов

### Запустить Odoo в интерактивном режиме

```bash
docker compose -f docker-compose.test.yml run --rm odoo_test bash

# Внутри контейнера:
odoo -d odoo_test -i currency_rate_update_by_nbb --test-enable --stop-after-init --log-level=debug
```

### Подключиться к работающему контейнеру

```bash
docker compose -f docker-compose.test.yml up -d
docker exec -it l10n_belarus_test_odoo bash
```

### Подключиться к БД PostgreSQL

```bash
docker exec -it l10n_belarus_test_db psql -U odoo -d odoo_test
```

## Полезные команды

### Очистить БД и начать заново

```bash
docker compose -f docker-compose.test.yml down -v
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Посмотреть логи

```bash
docker compose -f docker-compose.test.yml logs -f odoo_test
```

### Запустить тесты с coverage

```bash
docker compose -f docker-compose.test.yml run --rm odoo_test \
  coverage run --source=/mnt/extra-addons \
  /usr/bin/odoo -d odoo_test \
  -i currency_rate_update_by_nbb \
  --test-enable \
  --stop-after-init

# Посмотреть отчет
docker compose -f docker-compose.test.yml run --rm odoo_test coverage report
```

## CI/CD

GitHub Actions автоматически запускает тесты при каждом push. Результаты можно посмотреть:

```bash
gh pr checks 11 --repo OCA/l10n-belarus
```

Или в веб-интерфейсе:
https://github.com/OCA/l10n-belarus/pull/11/checks
