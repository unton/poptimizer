# Оптимизация долгосрочного портфеля акций

## Установка

Для установки необходимо:

- заполнить `.env.template` и переименовать его в `.env`
- установить [Task](https://taskfile.dev/installation/)
- установить [Scoop](https://scoop.sh/)
- установить [NodeJS](https://nodejs.org/en/download)
- установить [MongoDb Server](https://www.mongodb.com/try/download/community)
- установить [CUDA Toolkit](https://developer.nvidia.com/cuda-12-4-0-download-archive) (достаточно установить runtime)
- запустить команду установки необходимых инструментов

```bash
task install
```

- запустить MongoDB, которая указана в `.env`. Для локального запуска на MacOS

```bash
task mongo
```

- запустить программу

```bash
task run
```

- перейти по адресу, указанному `.env`
- добавить в настройках хотя бы один брокерский счет
- заполнить его актуальной информацией по имеющимся акциям и денежным средствам

# Обновление

После обновление необходимо пересобрать frontend

```bash
task build
```
