SELECT c.id_cliente, c.idade, c.canal, ci.cidade, ci.populacao,
       (DATE '{corte}' - c.data_cadastro)                       AS dias_cadastro,
       COUNT(p.id_pedido)                                       AS qtd_pedidos,
       COALESCE(SUM(p.valor), 0)::float                         AS total_gasto,
       COALESCE(AVG(p.valor), 0)::float                         AS ticket_medio,
       COALESCE(DATE '{corte}' - MAX(p.data_pedido), 999)       AS dias_desde_ultimo,
       COUNT(DISTINCT p.categoria)                              AS categorias_distintas
FROM dim_cliente c
JOIN dim_cidade ci ON ci.id_cidade = c.id_cidade
LEFT JOIN fato_pedido p ON p.id_cliente = c.id_cliente AND p.data_pedido < DATE '{corte}'
GROUP BY c.id_cliente, ci.id_cidade;
