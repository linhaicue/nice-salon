# D2 Fact Reliability Report

研究日期：2026-09-15（Asia/Shanghai）
目标：验证 C2“预约 → 到店 → 服务完成 → 复约”所需的最小事实，是否能从美管加稳定、只读、可关联、可追溯地获得。

## 结论

**D2 FAIL。C2 不能进入 D3。应按 D1 的回退条件重新打开 D1，并优先评估 C4“需求 × 产能错配”。**

失败原因不是“没有看到一个叫复约率的报表”，而是目前没有证据证明预约、到店、服务完成、复约这四个事实可以被定义、关联和重复获取为一条真实记录链。

本轮补充的门店经营事实进一步强化了这个结论：预约和短信功能没有实际进入门店日常经营。因而 C2 的问题不只是“技术事实暂未找到”，而是它依赖的预约→到店→复约工作流当前并没有真实发生。即使未来能够摸清相关接口，C2 也不适合作为当前门店的首条 AI 化闭环；只有门店真实采用预约流程后，才值得重新评估。

本报告没有修改 Master Map、GitHub issue 或美管加，也没有重放未知请求。当前浏览器连接在初始化时返回 `Unable to load browser request-header policy`，所以本轮没有新的在线业务响应。

## 证据边界

证据按以下等级使用：

| 等级 | 含义 |
| --- | --- |
| `HISTORICAL_FIRST_HAND` | 2026-09-11 至 2026-09-14 的已登录美管加页面只读探索记录；原始项目位于另一工作区，当前 `D:\nice` 不包含这些文件，因此只能作为历史证据，不能当作当前运行时合同。 |
| `HISTORICAL_CONTRACT` | 历史项目中已验证的水单列表/详情只读合同和脱敏回放记录；只覆盖账单域。 |
| `DISCOVERY_METADATA_ONLY` | 2026-09-15 对营业记录 source-page 的受控观察，只保留请求元数据和字段名/类型，未保留业务响应正文；不能证明预约或复约事实。 |
| `CURRENT_UNKNOWN` | 本轮无法通过当前浏览器或当前仓库的一手文件证明的内容。 |

补充证据：门店经营负责人确认预约和短信不是当前日常工作流。该信息用于判断 `Workflow Reality`，不替代对系统字段和接口的技术验证。

历史项目明确规定：预约、会员和其他候选路由属于观察或 Discovery 结果时，不能自动晋级正式采集合同；正式水单合同只有列表和详情两条。因此下面把候选路径写成“来源线索”，不写成可调用 API。

## 事实卡 1：`reservation`

| 字段 | 证据与结论 |
| --- | --- |
| 业务定义 | 历史领域词表把 `Appointment` 定义为预约事件，并明确要求把“未到店、已到店、取消”与消费事实区分。未证明供应商是否以同一事件状态表达这些状态。**结论：部分明确，状态语义 UNKNOWN。** |
| 页面入口 | 历史只读探索到预约记录日历 `reserv!reserv`，时间网格约为 10:00–21:00、30 分钟；另有预约休假设定 `reserv!reservrest`。创建预约按钮未操作。 |
| 观察到的请求 | 历史规格列出候选 `/shair/reservation!list.action`、`/shair/metedata!reservationMetadata.action`、`/shair/reservation!getShopReservationsNum.action`。它们是 Discovery/候选来源线索，不是当前正式合同；本报告没有重放。 |
| 唯一 ID | `appointment_id` 的概念出现在历史规格中，但没有当前可复核的真实预约记录或字段值。**UNKNOWN。** |
| `customer_id` | 历史规格要求预约与顾客关联，但没有真实预约响应字段证据。**UNKNOWN。** |
| `employee_id` | 页面可按员工/时段理解预约的可能性未形成一条可复核记录；字段和覆盖率 **UNKNOWN**。 |
| `service_id` | 未取得真实预约记录；**UNKNOWN**。 |
| `created_at` | **UNKNOWN**。 |
| `scheduled_at` | 日历格提供日期/时段的界面事实，但每条记录的可靠字段、时区和更新时间未证明。**部分可见，不能作为已确认字段。** |
| `updated_at` | **UNKNOWN**。 |
| `status` | 未证明“待到店、已到店、取消、改期、爽约”等状态枚举及其写入规则。**UNKNOWN。** |
| 分页 | **UNKNOWN**。 |
| 时间过滤 | 页面有前一天/后一天导航；没有证明底层列表的时间过滤参数、边界和时区。**UNKNOWN。** |
| 是否可增量 | 没有稳定 ID + `updated_at`/游标证据。**UNKNOWN。** |
| 记录覆盖情况 | 历史页面抽查显示 2026-09-11、09-12、09-13、09-14 连续日历为空，历史记录也为空；这支持“当前门店预约模块趋近未使用”的假设，但不能证明全系统没有预约。**覆盖不足，结论为 UNKNOWN/高风险。** |
| 已知例外 | 空日历可能是门店未使用、筛选范围不对、权限范围不全或历史深度不足；不能把空结果当作“预约事实为零”。 |
| 证据来源 | `HISTORICAL_FIRST_HAND`：历史 `docs/discovery/capability-atlas.md` 的 Appointment Domain/Step 1 记录；历史 `docs/discovery/meiguanjia-current.md` 的 Appointment 词表。当前仓库不含这些源文件。 |
| 结论 | **FAIL（对 C2 不可用）**：页面入口存在，但没有可用的真实记录、状态语义、稳定身份键和重复读取合同。 |

## 事实卡 2：`arrival`

| 字段 | 证据与结论 |
| --- | --- |
| 业务定义 | 历史资料只提出必须区分“未到店、已到店、取消”与消费事实，没有证明“已到店”由谁记录、在什么动作发生时写入、是否等于开始服务。**UNKNOWN。** |
| 页面入口 | 未发现可单独复核的到店事实页面。理论上可能位于预约日历或营业/排队页面，但本轮不能补猜。**UNKNOWN。** |
| 观察到的请求 | 没有可复核的 arrival 专属请求。预约候选路径不能被当作 arrival 请求。 |
| 唯一 ID | **UNKNOWN。** |
| `customer_id` | **UNKNOWN。** |
| `employee_id` | **UNKNOWN。** |
| `service_id` | **UNKNOWN。** |
| `created_at` | **UNKNOWN。** |
| `scheduled_at` | 只能继承预约候选的时段概念，不能证明到店记录拥有该字段。**UNKNOWN。** |
| `updated_at` | **UNKNOWN。** |
| `status` | “已到店”是否是预约状态、排队状态或人工标记，**UNKNOWN**。 |
| 分页 | **UNKNOWN。** |
| 时间过滤 | **UNKNOWN。** |
| 是否可增量 | **UNKNOWN**；没有稳定事件 ID 或更新时间证据。 |
| 记录覆盖情况 | 因预约日历连续为空，无法估计 arrival 覆盖率。**UNKNOWN。** |
| 已知例外 | 到店但未产生消费、到店后取消、跨员工服务、改期和散客都可能使“到店”与“服务完成”分离；当前没有供应商口径证据。 |
| 证据来源 | 历史 Appointment 定义中的“未到店/已到店/取消需与消费事实区分”；没有 arrival 记录。 |
| 结论 | **UNKNOWN（对 C2 不可用）**：到店没有独立、可关联、可重复读取的事实证据。 |

## 事实卡 3：`service_completion`

| 字段 | 证据与结论 |
| --- | --- |
| 业务定义 | 历史水单域已确认：正常水单中的项目消费可作为一次有效服务访问的边界；同单明细合并，一项多员工不增加访问次数。这个事实可支持“已发生项目消费”，但没有证明供应商把它命名或记录为“服务完成”。**结论：可用代理事实，业务语义仍需谨慎。** |
| 页面入口 | 营业记录/水单审查 source-page：`/shair/bill!billcheck.action?set=manage`；详情候选：`/shair/bill!detail.action`。历史水单列表/详情属于已验证的只读合同，但不是预约链路合同。 |
| 观察到的请求 | 历史正式合同：`/shair/bill!billcheckData.action`、`/shair/bill!detail.action`。本轮没有重放；2026-09-15 的 source-page Discovery 只产生 `request-metadata-only`，63 条被动资源均在发送前中止，没有业务正文。 |
| 唯一 ID | 历史账单结构包含 `vendor_bill_id`/`bill_id`，明细包含 `bill_item_id`。**HISTORICAL_CONTRACT：已见结构；当前值不在仓库。** |
| `customer_id` | 历史账单结构要求 `customer_ref`，并以租户 + 稳定供应商顾客 ID 作为身份边界；散客可未关联。**历史结构已确认，当前实时覆盖 UNKNOWN。** |
| `employee_id` | 历史账单明细员工关系包含 `employee_ref`；多员工是关系数量而非访问数量。**历史结构已确认，当前覆盖 UNKNOWN。** |
| `service_id` | 历史明细包含 `service_ref` 和原始项目字段；未知项目映射必须保留 `unknown`。**历史结构已确认，当前覆盖 UNKNOWN。** |
| `created_at` | **UNKNOWN**；历史字段重点是消费时间，不足以证明创建时间。 |
| `scheduled_at` | **N/A/UNKNOWN**：水单事实本身没有预约时段，不能由账单补写。 |
| `updated_at` | **UNKNOWN**。 |
| `status` | 历史真实对照确认 `status=0` 出现在正常水单详情，`status=1` 出现在带撤销原因的销单记录；未知枚举仍需 fail-closed。 |
| 分页 | 历史采集曾覆盖约 180 天账单窗口，但当前 D2 没有证明预约/到店的分页行为；水单分页不能替代预约分页。 |
| 时间过滤 | 历史账单采集使用日期窗口；精确边界、时区、更新时间游标和遗漏补偿未在当前仓库证明。 |
| 是否可增量 | 水单可按账单 ID/日期窗口做重复采集的方向已验证，但 `updated_at`/增量游标没有完成 D2 所需证明。**部分。** |
| 记录覆盖情况 | 历史水单域有真实脱敏回放和 180 天样本；这只证明消费事实，不证明预约、到店和复约覆盖。 |
| 已知例外 | 散客身份可能未关联；取消/撤销不能进入有效生命周期；一单多明细不等于多次到店；套餐购买与实际服务核销要分开。 |
| 证据来源 | 历史 `docs/discovery/meiguanjia-current.md`、`docs/discovery/history/2026-09-11.md`、历史水单正式合同/脱敏 replay 记录；当前仓库不含这些文件。 |
| 结论 | **PARTIAL**：能证明“正常水单/项目消费”这一账单事实链，但不能把它升级为预约后的服务完成事件，也不能单独支撑 C2。 |

## 事实卡 4：`rebooking`

| 字段 | 证据与结论 |
| --- | --- |
| 业务定义 | **UNKNOWN。** 未证明复约是服务完成后现场预约、未来任意预约、提前预约下一次、系统推断还是人工录入；取消、改期、跨员工预约的处理规则也未证明。 |
| 页面入口 | 没有取得复约原始记录的独立页面入口。历史对话提到供应商已有“复约”类分析指标，但该二手描述不等于原始复约事实。**UNKNOWN。** |
| 观察到的请求 | 没有可复核的 rebooking 请求。预约列表候选路径不能证明复约语义。 |
| 唯一 ID | **UNKNOWN。** |
| `customer_id` | **UNKNOWN。** |
| `employee_id` | **UNKNOWN。** |
| `service_id` | **UNKNOWN。** |
| `created_at` | **UNKNOWN。** |
| `scheduled_at` | **UNKNOWN。** |
| `updated_at` | **UNKNOWN。** |
| `status` | **UNKNOWN。** |
| 分页 | **UNKNOWN。** |
| 时间过滤 | **UNKNOWN。** |
| 是否可增量 | **UNKNOWN。** |
| 记录覆盖情况 | 没有原始记录样本，不能估计；供应商报表中的聚合指标不能替代覆盖率验证。 |
| 已知例外 | 现场复约、事后电话/短信预约、改期、取消后重约、跨员工重约均可能改变口径；当前没有证据区分。 |
| 证据来源 | 当前没有一手 rebooking 事实来源；历史项目只把预约域列为待深入、且连续采样为空。 |
| 结论 | **FAIL**：C2 的核心结果事实没有可验证定义、记录或覆盖率。 |

## 关系表

| 关系 | 直接 ID 关联 | 顾客 + 时间推断 | 当前结论 |
| --- | --- | --- | --- |
| `Reservation → Arrival` | 未证明 `appointment_id` 或其他直接边 | 理论上可用同一顾客 + 预约时段尝试，但没有 arrival 记录，不能执行 | **无法证明** |
| `Arrival → Service Completion` | 未证明 arrival ID、bill ID 或服务事件 ID 的直接边 | 顾客 + 相近时间只能形成候选匹配；跨员工、散客、改期和同日多单会产生歧义 | **无法证明** |
| `Service Completion → Rebooking` | 未发现复约记录或直接引用 | 顾客 + 后续预约时间只是推断，且预约域当前无样本 | **无法证明** |
| `Customer / Employee / Service` 分组 | 水单域历史结构分别有顾客、员工、项目引用 | 对预约/到店/复约没有相同字段证据 | **仅账单局部成立** |

严禁把上述“顾客 + 时间”推断写入事实层。没有直接 ID 或经人工复核的匹配证据时，最多只能标为候选关系；本 D2 没有足够样本形成候选关系。

## D2 PASS 条件逐项判断

| PASS 条件 | 判断 | 依据 |
| --- | --- | --- |
| 1. 四个核心概念定义基本明确 | **FAIL** | 服务消费可部分定义；预约状态、到店和复约口径未明确。 |
| 2. 预约 → 到店 → 服务完成能稳定关联顾客和时间 | **FAIL** | 预约连续空；arrival 无事实；只有账单局部证据。 |
| 3. 员工、项目关联足够可靠，可支撑分组比较 | **UNKNOWN / PARTIAL** | 水单的员工/项目结构有历史证据；预约链路覆盖和一致性未知。 |
| 4. 复约含义和覆盖率足够一致 | **FAIL** | 没有原始复约事实、定义或覆盖样本。 |
| 5. 只读条件下可重复获取 | **FAIL** | 账单合同可历史重复获取；预约/到店/复约未形成合同；当前浏览器不可用。 |
| 6. 可识别新增、更新、取消 | **PARTIAL / FAIL** | 水单 `status=0/1` 有历史语义；预约及复约的更新时间、状态和增量规则未知。 |
| 7. 关键事实保留来源和采集时间 | **PARTIAL** | 历史报告保留来源/观察时间，但业务正文未进入当前仓库；预约链路本身没有可追溯事实。 |

## D2 决策

当前决策为：

```text
D2 = FAIL
C2 不能进入 D3
重新打开 D1
优先评估 C4：需求 × 产能错配
```

## Workflow Reality 补充判断

D1 的候选筛选增加第八项：

```text
Workflow Reality
门店现实中是否真的存在并重复发生这条工作流
```

当前对 C2 的判断为：

```text
预约/短信功能存在于系统
        ≠
门店日常使用预约/短信工作流
```

因此 C2 在 `Workflow Reality` 上不通过。C4“需求 × 产能错配”成为优先候选，但仍需在 D1 中验证水单、员工可用性、项目能力、耗时和历史基线是否足以形成真实闭环。

这不是把“复约”判定为门店一定不存在，而是判定：在当前证据边界内，它还不能承担 C2 第一次证明所要求的事实角色。若后续重新获得已登录页面，应先完成预约域的用户确认、真实记录采样和状态语义对照；在此之前不要设计正式 Schema、Customer Profile、Employee Profile、Memory、Agent 或 Action 系统。

## 证据索引

- GitHub D1 决策：[D1 — 第一条值得 AI 化的经营决策是什么？](https://github.com/linhaicue/nice-salon/issues/2)
- GitHub D2 任务：[D2 — 如何稳定获得第一条闭环所需事实？](https://github.com/linhaicue/nice-salon/issues/3)
- 历史美管加页面观察（不在当前 `D:\nice` checkout）：`D:\lifa\docs\discovery\capability-atlas.md`，Appointment Domain 与 Step 1 记录。
- 历史美管加事实词表（不在当前 `D:\nice` checkout）：`D:\lifa\docs\discovery\meiguanjia-current.md`，Appointment 定义及历史证据边界。
- 历史水单语义对照（不在当前 `D:\nice` checkout）：`D:\lifa\docs\discovery\history\2026-09-11.md`，水单 `status/type` 语义和脱敏 replay。
- 2026-09-15 受控 source-page 观察：`.scratch/discovery-p1-observations-2026-09-15T04-58-43-368Z.json`（历史工作区产物；`request-metadata-only`、63 条被动资源观察、无业务响应正文）。
- 当前浏览器检查：cua `getState()` 返回 `Unable to load browser request-header policy`；因此本轮没有新的在线业务证据。
