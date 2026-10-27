# BarberFlow

API REST de agendamento para barbearia, com autenticação JWT e níveis de permissão (`CLIENTE`, `BARBEIRO` e `ADMIN`).

> **Status:** em desenvolvimento. Autenticação, permissões, catálogo de serviços, horários dos barbeiros, criação, listagem e cancelamento de agendamentos estão implementados. A suíte automatizada contém 53 testes aprovados.

## Stack

- Python 3
- Flask (application factory + Blueprints)
- Flask-SQLAlchemy / SQLAlchemy 2
- MySQL (driver PyMySQL)
- Flask-JWT-Extended
- python-dotenv

## Funcionalidades

**Prontas**

- Cadastro de usuários com senha em hash
- Login com JWT (validade de 1 hora)
- Rotas protegidas e controle de acesso por role
- Gestão de usuários pelo admin (editar e desativar)
- CRUD de serviços (corte, barba etc.): leitura para qualquer usuário logado, escrita só para admin
- Cadastro de horários de atendimento dos barbeiros pelo admin
- Criação de agendamentos por usuários autenticados, com validação de expediente e conflito
- Listagem de agendamentos conforme a role atual do usuário no banco
- Cancelamento pelo cliente dono ou pelo admin

**Melhorias planejadas**

- Migrations (Flask-Migrate)
- Documentação da API (Swagger/OpenAPI)
- Docker e docker-compose
- Limite de tentativas no login


## Estrutura do projeto

```
barberflow/
├── app/
│   ├── __init__.py        # create_app(): configura, liga extensões, registra Blueprints
│   ├── ext.py             # db e jwt (criados sem app, ligados no create_app)
│   ├── models/
│   │   ├── user.py        # usuários, role e estado ativo
│   │   ├── service.py     # serviços e duração
│   │   ├── horarios.py    # expediente semanal do barbeiro
│   │   └── agendamento.py # cliente, barbeiro, serviço e período
│   ├── routes/
│   │   ├── main.py        # rota de verificação
│   │   ├── auth.py        # cadastro, login, /me e gestão de usuários
│   │   ├── serv.py        # CRUD de serviços
│   │   ├── barber.py      # consulta de barbeiros e horários
│   │   └── agen.py        # criação, listagem e cancelamento
│   └── utils/
│       └── decorators.py  # @role_required
├── tests/
│   ├── conftest.py        # app, SQLite em memória e cliente de teste
│   ├── test_auth.py
│   ├── test_serv.py
│   ├── test_barber.py
│   └── test_agen.py
├── .env.example           # modelo das variáveis de ambiente
├── requirements.txt
├── requirements-dev.txt   # dependências de desenvolvimento e teste
└── run.py                 # sobe a API
```

## Como rodar

**1. Clone e crie o ambiente virtual**

```bash
git clone https://github.com/Thiago-mcm/barberflow.git
cd barberflow
python -m venv .venv
```

Ative o ambiente (`.venv\Scripts\activate` no Windows, `source .venv/bin/activate` no Linux/Mac) e instale as dependências:

```bash
pip install -r requirements.txt
```

**2. Crie o banco no MySQL**

```sql
CREATE DATABASE barberflow;
```

**3. Configure as variáveis de ambiente**

Copie o `.env.example` para `.env` e preencha:

```
DB_URI=mysql+pymysql://usuario:senha@localhost:3306/barberflow
JWT_SECRET_KEY=cole_aqui_uma_chave_aleatoria
```

Para gerar a chave:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> Se a senha do banco tiver caracteres especiais (`@`, `#`, `/`), eles precisam ser codificados na URL.

**4. Rode a API**

```bash
python run.py
```

As tabelas são criadas automaticamente na primeira execução. A API sobe em `http://127.0.0.1:5000`.

**5. Crie um administrador**

Todo cadastro pela API nasce como `CLIENTE`. Para promover um usuário, cadastre-o normalmente e rode no MySQL:

```sql
UPDATE users SET role = 'ADMIN' WHERE email = 'admin@exemplo.com';
```

A role é consultada no banco a cada requisição protegida. Depois da alteração, o usuário pode continuar usando o token atual; a nova role será aplicada nas próximas requisições.

## Testes automatizados

Os testes usam SQLite em memória e o cliente de teste do Flask. O servidor não precisa estar rodando e o banco MySQL de desenvolvimento não é usado.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

A suíte atual tem 53 testes aprovados, cobrindo autenticação, permissões, serviços, horários dos barbeiros e agendamentos.

## Autenticação

1. `POST /auth/register` cria o usuário.
2. `POST /auth/login` devolve um `access_token`.
3. Nas demais rotas, envie o token no cabeçalho:

```
Authorization: Bearer <access_token>
```

Exemplo de cadastro:

```json
{
  "nome": "Maria Silva",
  "email": "maria@exemplo.com",
  "senha": "senha12345"
}
```

Exemplo de serviço (`POST /serv/add`, só admin):

```json
{
  "nome": "Corte",
  "preco": 35.00,
  "duracao": 30
}
```

## Endpoints

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/` | público | verifica se a API está no ar |
| POST | `/auth/register` | público | cria usuário (sempre como `CLIENTE`) |
| POST | `/auth/login` | público | devolve o `access_token` |
| GET | `/auth/me` | logado | dados do usuário autenticado |
| PATCH | `/auth/edit/<id>` | `ADMIN` | edita `nome` e/ou `email` de um usuário |
| DELETE | `/auth/delete/<id>` | `ADMIN` | desativa um usuário |
| GET | `/serv/consult` | logado | lista os serviços ativos |
| GET | `/serv/consult/<id>` | logado | detalha um serviço ativo |
| POST | `/serv/add` | `ADMIN` | cria serviço |
| PATCH | `/serv/edit/<id>` | `ADMIN` | atualiza serviço (parcial) |
| DELETE | `/serv/delete/<id>` | `ADMIN` | desativa serviço |
| GET | `/barber/consult` | logado | lista barbeiros ativos |
| POST | `/barber/horario` | `ADMIN` | cadastra expediente de barbeiro |
| GET | `/barber/consult/<id_barbeiro>` | logado | lista horários de um barbeiro |
| DELETE | `/barber/del/<id_hr>` | `ADMIN` | remove horário de expediente |
| POST | `/agen/add` | logado | cria agendamento associado ao usuário autenticado |
| GET | `/agen/list` | logado | lista agendamentos conforme a role |
| DELETE | `/agen/del/<id_agen>` | dono ou `ADMIN` | cancela agendamento |

## Regras de negócio

### Usuários

- O cadastro **não aceita `role`**: todo usuário nasce `CLIENTE`. Promoções são feitas direto no banco.
- O email é normalizado (sem espaços, em minúsculas) e é único.
- A senha precisa ter pelo menos 8 caracteres e é guardada apenas como hash.
- Usuários não são apagados: `DELETE` apenas os desativa (`ativo = false`), preservando o histórico para os agendamentos.
- Usuário desativado: não consegue entrar (`403`, depois de confirmar a senha); requisições protegidas com um token já emitido respondem `401`. O email continua reservado (cadastro com ele dá `409`).
- O admin não pode desativar a própria conta.
- A edição altera só `nome` e `email`. Role e senha não podem ser alteradas pela API.

### Serviços

- Qualquer usuário logado lista e consulta. Só o admin cria, edita e desativa.
- A listagem mostra apenas serviços ativos, em ordem alfabética.
- `nome`: obrigatório, até 100 caracteres, único.
- `preco`: número maior que zero e menor que 100000, guardado como decimal com 2 casas.
- `duracao`: inteiro maior que zero, em minutos. Valores booleanos são rejeitados.
- A atualização é parcial: só muda os campos enviados, e toda a validação acontece antes de gravar.
- Serviço desativado se comporta como inexistente (`404`).

### Horários e criação de agendamentos

- Só um `ADMIN` pode cadastrar ou remover horários de atendimento.
- O expediente usa o dia da semana de `0` (segunda-feira) a `6` (domingo), com horários de início e fim.
- Qualquer usuário autenticado (`CLIENTE`, `BARBEIRO` ou `ADMIN`) pode criar um agendamento. O campo `cliente_id` é definido pelo usuário identificado no token; esse campo não é aceito do corpo da requisição.
- O corpo de criação contém `barbeiro_id`, `servico_id` e `inicio`. O início usa o formato `YYYY-MM-DDTHH:MM`, por exemplo `2026-10-26T10:00`.
- O barbeiro precisa existir, estar ativo e ter role `BARBEIRO`; o serviço precisa existir e estar ativo.
- O fim é calculado somando a duração do serviço ao início. O agendamento precisa começar no futuro e terminar no mesmo dia.
- Um único horário de expediente precisa cobrir o intervalo inteiro. Expedientes encostados não são unidos: com horários 09:00–12:00 e 12:00–14:00, um agendamento que atravesse 12:00 é recusado.
- Não pode haver sobreposição com outro agendamento `CONFIRMADO` do mesmo barbeiro. A verificação usa `novo_inicio < fim_existente` e `novo_fim > inicio_existente`; portanto, horários que apenas encostam são permitidos. Agendamentos `CANCELADO` não bloqueiam.
- A criação retorna `201`; dados inválidos retornam `400`, barbeiro ou serviço indisponível retorna `404`, e horário fora do expediente ou ocupado retorna `409`.
- Duas requisições simultâneas para o mesmo horário ainda podem passar pela validação antes de qualquer uma gravar; essa condição de corrida será tratada futuramente.
- A listagem mostra somente agendamentos `CONFIRMADO`, em ordem de início: `CLIENTE` vê os próprios, `BARBEIRO` vê os seus e `ADMIN` vê todos os confirmados.
- Sem resultados, a listagem responde `200` com `"agendamentos": []`.
- O cancelamento não apaga a linha: altera o status para `CANCELADO`. O dono ou `ADMIN` pode cancelar; outro cliente recebe `403`, ID inexistente recebe `404` e agendamento já cancelado recebe `409`.
- O cliente precisa cancelar com pelo menos 2 horas de antecedência. O admin pode cancelar sem prazo. Tentativa do cliente fora do prazo retorna `400`.

## Decisões de segurança

- **Hash de senha** com `generate_password_hash`, nunca texto puro. A resposta da API nunca inclui o hash.
- **Mesma mensagem e `401`** para email inexistente e senha errada, para não revelar quais emails estão cadastrados.
- **Conta desativada** só é revelada depois de a senha ser confirmada, pelo mesmo motivo.
- **Role fora do alcance do cliente**: não vem no cadastro nem na edição.
- **Token com expiração** de 1 hora.
- **Segredos em variáveis de ambiente**: o `.env` fica fora do Git e o `.env.example` serve de modelo.
- **Validação de tipo antes de comparação** nos campos numéricos, para entrada inválida resultar em `400` e não em erro interno.
- **Exclusão lógica** em usuários e serviços, para não quebrar o histórico.

## Códigos de status

| Código | Significado | Exemplo |
|---|---|---|
| `200` | sucesso | login, listagens, atualizações e cancelamento |
| `201` | criado | cadastro, criação de serviço e agendamento |
| `400` | dados inválidos | campo faltando, preço negativo, senha curta |
| `401` | não autenticado | senha errada, token ausente ou expirado |
| `403` | sem permissão | cliente em rota de admin ou tentando cancelar agendamento alheio |
| `404` | não encontrado | id inexistente ou desativado |
| `409` | conflito | email/nome já cadastrado, horário ocupado ou agendamento já cancelado |
| `422` | token malformado | token adulterado (padrão da biblioteca JWT) |

## Limitações conhecidas

- **Role e estado ativo são consultados no banco.** Alterar a role ou desativar a conta afeta as próximas requisições protegidas, mesmo com um token já emitido. O token continua sujeito à expiração de 1 hora.
- Emails e nomes de serviço continuam únicos mesmo depois de desativados.
- As tabelas são criadas com `db.create_all()`, que não altera tabelas já existentes. Ainda não há sistema de migrations.
- A criação de agendamentos usa `DateTime` para início e fim. Se a tabela `agendamentos` já existia com colunas `TIME`, ela precisa ser migrada ou recriada em banco de desenvolvimento; `create_all()` não altera o tipo existente.
- O `run.py` sobe o servidor de desenvolvimento do Flask (modo debug). Não use em produção.
- Ainda não há limite de tentativas no login.
- Os nomes das rotas (`/consult`, `/add`, `/edit/<id>`, `/delete/<id>`) usam verbos na URL. O padrão REST seria o método HTTP indicar a ação.

## Roadmap

- [x] Estrutura do projeto (application factory e Blueprints)
- [x] Cadastro e login com JWT
- [x] Rotas protegidas e permissões por role
- [x] CRUD de serviços
- [x] Gestão de usuários (editar e desativar)
- [x] Horários de atendimento dos barbeiros
- [x] Criação de agendamentos com validação de expediente e conflito
- [x] Listagem e cancelamento com regra de prazo e de dono
- [x] Testes automatizados de autenticação, permissões, serviços, horários e agendamentos
- [ ] Migrations (Flask-Migrate)
- [ ] Documentação da API (Swagger/OpenAPI)
- [ ] Docker e docker-compose
- [ ] Limite de tentativas no login

## Autor

Thiago Martins Costa Mello. [GitHub](https://github.com/Thiago-mcm)







